pipeline {
    agent any

    environment {
        REMOTE_USER = 'kama'
        REMOTE_HOST = '192.168.1.175'
        PROJECT_DIR = '/home/kama/TelegramBotEconomyAdmin'
    }

    stages {
        stage('Checkout') {
            steps {
                // Checkout the latest code from GitHub to Jenkins workspace
                git url: 'https://github.com/yourusername/your-repo.git', branch: 'master'
            }
        }

        }
    }

    post {
        failure {
            mail to: 'your-email@example.com',
                 subject: "Failed Pipeline: ${currentBuild.fullDisplayName}",
                 body: "Something went wrong. Please check the logs."
        }
    }
}
