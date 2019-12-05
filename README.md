# Overview
Based on errbot 5.2 this project deploys a slack bot

## Plugins
- GSuiteCmds - Plugin that enables users to run administrative commands for GSuite

## Deployment

1. Edit `docker-compose.yml` with appropriate environment variables (e.g. `BOT_TOKEN`)
2. Run `docker-compose -f "${IT_BOT_DIR}/docker-compose.yml" up --build -d` where `${IT_BOT_DIR}` is the directory of the project.
