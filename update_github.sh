#!/bin/bash

# Load the GitHub token from a file
GITHUB_TOKEN=$(cat /root/.github_token)

# Load Git user name and email from the configuration file
source /root/.gitconfig_info

# Configure git to use the token for authentication
git config --global --add safe.directory /code/startercode-generator-bs/_work

# Configure user name and email for Git commits
git config --global user.email "$GIT_USER_EMAIL"
git config --global user.name "$GIT_USER_NAME"

# Change to the appropriate directory
cd /code/startercode-generator-bs/_work

# Set the remote URL with the token (you might need to update the repository URL)
git remote set-url origin https://$GIT_USER_NAME:${GITHUB_TOKEN}@github.com/opendatabs/startercode-opendatabs.git

# Pull the latest changes
git pull

# Add all changes
git add .

# Commit the changes
git commit -m "Regular update of all starter codes"

# Push the changes
git push
