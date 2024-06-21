pipeline {
    agent any


    stages {
        stage('Checkout') {
            steps {
                // Checkout the latest code from GitHub to Jenkins workspace
                git url: 'https://github.com/Kama17/TelegramBotEconomyAdmin.git', branch: 'main'
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
