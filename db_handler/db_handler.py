from datetime import datetime
import sqlite3
from logger_handler.logger_config import setup_logger
from dateutil import parser
import csv

from config.setup import DB_PATH, FILE_PATH

logger = setup_logger()

class DatabaseHandler:
    def __init__(self, db_name=DB_PATH):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY,
            name TEXT,
            type TEXT
        )
        ''')
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            chat_id INTEGER,
            user_id INTEGER PRIMARY KEY,
            access_hash INTEGER,
            economy_id TEXT,
            first_name TEXT,
            last_name TEXT,
            username TEXT
        )
        ''')
        self.cursor.execute('''
                            CREATE TABLE IF NOT EXISTS enrollment_renewals (
                            economy_id TEXT PRIMARY KEY,
                            level INTEGER,
                            first_name TEXT,
                            last_name TEXT,
                            status BOOL,
                            customer_type TEXT,
                            autoship_date DATE,
                            binary_leg TEXT,
                            active_kit_order BOOL,
                            FOREIGN KEY (economy_id) REFERENCES users(economy_id))''')

        index_statements = [
        "CREATE INDEX IF NOT EXISTS idx_users_economy_id ON users(economy_id);",
        "CREATE INDEX IF NOT EXISTS idx_enrollment_renewals_economy_id ON enrollment_renewals(economy_id);",
        "CREATE INDEX IF NOT EXISTS idx_enrollment_renewals_autoship_date ON enrollment_renewals(autoship_date);",
        "CREATE INDEX IF NOT EXISTS idx_enrollment_renewals_active_kit_order ON enrollment_renewals(active_kit_order);"
        ]
        for statement in index_statements:
            self.cursor.execute(statement)

        self.conn.commit()
        logger.info("Tables created successfully")


    def check_member_exists(self, user_id):
        self.cursor.execute('''
                SELECT EXISTS(SELECT 1 FROM users WHERE user_id = ?)
                ''', (user_id,))

        return self.cursor.fetchone()[0]

    def add_member(self, chat_id, user_id, access_hash, first_name, last_name, username):

        if(self.check_member_exists(user_id)):

            self.cursor.execute('''
                UPDATE users
                SET
                chat_id = COALESCE(?, chat_id),
                access_hash = COALESCE(?, access_hash),
                first_name = COALESCE(?, first_name),
                last_name = COALESCE(?, last_name),
                username = COALESCE(?, username),
                WHERE user_id = ?
            ''', (chat_id, access_hash, first_name, last_name, username))
            logger.info(f"Updated member {username} (ID: {user_id}) in chat {chat_id}")
        else:

            self.cursor.execute('''
                                INSERT INTO users (
                                chat_id,
                                user_id,
                                access_hash,
                                economy_id,
                                first_name,
                                last_name,
                                username)
                                VALUES (?, ?, ?, ?, ?, ?, ?)''',
                                (chat_id, user_id, access_hash, None, first_name, last_name, username))
            logger.info(f"Added member {username} (ID: {user_id}) in chat {chat_id}")
        self.conn.commit()

    def add_chat_users(self, users_list, chat_id):
        for user in users_list:
            if not user.bot:
                self.add_member(chat_id, user.id, user.access_hash, user.first_name, user.last_name, user.username)

    def add_chat(self, chat_id, chat_name, chat_type):
        self.cursor.execute('''
                            INSERT OR REPLACE INTO chats (
                            id,
                            name,
                            type) VALUES (?, ?, ?)''',
                            (chat_id, chat_name, chat_type))
        self.conn.commit()
        logger.info(f"Added/Updated chat {chat_name} (ID: {chat_id}, Type: {chat_type})")

    def update_chat_id(self, old_id, new_id):
        self.cursor.execute('''
                            UPDATE chats
                            SET id = ? WHERE id = ?''',
                            (new_id, old_id))
        self.conn.commit()
        logger.info(f"Updated chat ID from {old_id} to {new_id}")

    def close(self):
        self.conn.close()
        logger.info("Database connection closed")


    def enrollment_renewals(self):

        self.cursor.execute('DELETE FROM enrollment_renewals')

        insert_sql = '''
                    INSERT INTO enrollment_renewals (economy_id, level, first_name, last_name, status, customer_type, autoship_date, binary_leg, active_kit_order)
                    VALUES (:economy_id, :level, :first_name, :last_name, :status, :customer_type, :autoship_date, :binary_leg, :active_kit_order)
                    '''

        with open(FILE_PATH, 'r') as file:
            # Create a CSV reader object
            csv_reader = csv.DictReader(file)

            for row in csv_reader:
                # Rename dictionary keys to match column names in SQL
                row['economy_id'] = row.pop('Id')
                 # Convert Level to integer if needed
                row['level'] = int(row['Level']) if row['Level'].isdigit() else None
                row['first_name'] = row.pop('First Name')
                row['last_name'] = row.pop('Last Name')
                row['status'] =row.pop('Status').strip().lower() == 'yes'
                row['customer_type'] = row.pop('Customer Type')
                row['autoship_date'] = self.parse_date(row.pop('Autoship Date'))
                row['binary_leg'] = row.pop('Binary Leg')
                row['active_kit_order'] = row.pop('Active Kit order').strip().lower() == 'yes'

                self.cursor.execute(insert_sql, row)

        self.conn.commit()
        logger.info(f"created enrollment_renewals!")

        self.update_economy_id()
        invalid_users = self.check_for_valid_user_name()
        ban_users = self.check_ban_member()
        return [invalid_users, ban_users]


    def parse_date(self, date_str):
        try:
            parsed_date = parser.parse(date_str)  # Attempt with day first
            return parser.parse(date_str).strftime('%Y-%m-%d %H:%M:%S')
        except ValueError:
            return None


    def update_economy_id(self):

        # Update user economy_id if the user name consist it. The economy_id is got form enrollment_renewals
        query = '''
                SELECT u.user_id, u.username, e.economy_id
                FROM users u
                JOIN enrollment_renewals e ON u.username LIKE '%' || e.economy_id || '%'
                '''

        users_to_update = self.cursor.execute(query).fetchall()

        for user in users_to_update:
            print(f"Updating economy_id (users table ): User name:{user[1]} Economy ID:{user[2]}")
            self.cursor.execute('''
                                UPDATE users
                                SET economy_id = ?
                                WHERE user_id = ? AND economy_id IS NULL
                            ''', (user[2], user[0]))

        self.conn.commit()

    def check_for_valid_user_name(self):

        query = '''
            SELECT username,economy_id, first_name, last_name
            FROM users
            WHERE economy_id IS NULL
        '''
        self.cursor.execute(query)
        invalid_users = self.cursor.fetchall()

        if invalid_users:
            for user in invalid_users:
                print(f"User name is invalid: {user[0]}")
        return invalid_users

    def check_ban_member(self):

        current_date = self.parse_date(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

        query = '''
        SELECT u.*
            FROM users u
            JOIN enrollment_renewals e ON u.economy_id = e.economy_id
            WHERE DATE(e.autoship_date) < DATE(?)
            AND e.active_kit_order = 0
        '''

        # Execute the query
        self.cursor.execute(query, (current_date,))

        # Fetch all results
        users_to_ban = self.cursor.fetchall()

        for user in users_to_ban:
            print(f"User to ban: User Name:{user[6]}, Economy ID: {3}")

        return users_to_ban




