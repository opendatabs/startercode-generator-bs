GITHUB_TOKEN=$(cat ~/.github_token)
git config --global --add safe.directory /code/startercode-generator-bs/_work
cd /code/startercode-generator-bs/_work
git remote set-url origin https://osaeedi:${GITHUB_TOKEN}@github.com/opendatabs/startercode-opendatabs.git
git pull
git add .
git commit -m "Regular update of all starter codes"
git push
