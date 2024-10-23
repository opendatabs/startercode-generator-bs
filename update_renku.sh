#!/bin/bash

# Load the GitLab token from a file
GITLAB_TOKEN=$(cat /root/.renku_token)
# Load Git user name and email from the configuration file
source /root/.gitconfig_info
# Configure git to use the token for authentication
git config --global --add safe.directory /code/startercode-generator-bs/_work_renku
# Configure user name and email for Git commits
git config --global user.email "$GIT_USER_EMAIL"
git config --global user.name "$GIT_USER_NAME"

# Change to the appropriate directory
cd /code/startercode-generator-bs/_work_renku
# Set the remote URL with the token (GitLab URL)
git remote set-url origin https://$GIT_USER_NAME:${GITLAB_TOKEN}@gitlab.renkulab.io/opendatabs/startercode-opendatabs.git
# Pull the latest changes
git pull

# Add all changes
git add .
# Get the current date and time
current_time=$(date +"%Y-%m-%d %H:%M:%S")
# Commit the changes
git commit -m "Regular update of all starter codes - $current_time"
# Push the changes
git push
