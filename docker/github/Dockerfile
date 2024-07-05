FROM ubuntu:latest
ARG https_proxy
ENV https_proxy=${https_proxy}
ARG GITHUB_TOKEN
ARG GIT_USER_EMAIL
ARG GIT_USER_NAME
RUN echo "${GITHUB_TOKEN}" > /root/.github_token && \
    echo "GIT_USER_EMAIL=${GIT_USER_EMAIL}" > /root/.gitconfig_info && \
    echo "GIT_USER_NAME=${GIT_USER_NAME}" >> /root/.gitconfig_info
RUN apt-get update && apt-get install -y git
WORKDIR /code/startercode-generator-bs
CMD ["/bin/bash", "/code/startercode-generator-bs/update_github.sh"]

# Docker commands to create image and run container:
# cd docker/github
# docker build --build-arg https_proxy="http://your-proxy-server:port" -t update_github .
# cd ../.
# docker run -it --rm -e https_proxy="http://your-proxy-server:port" -v /data/dev/workspace/startercode-generator-bs:/code/startercode-generator-bs --name update_github update_github
