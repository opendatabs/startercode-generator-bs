FROM python:3.11-bullseye
WORKDIR /code/startercode-generator-bs
#ARG HTTPS_PROXY
#ENV HTTPS_PROXY=$HTTPS_PROXY
RUN python3 -m pip install --user --no-cache-dir pandas==2.2.0
RUN python3 -m pip install --user --no-cache-dir requests==2.31.0
RUN python3 -m pip install --user --no-cache-dir tqdm==4.66.4
CMD ["python3", "-m", "updater"]


# Docker commands to create image and run container:
# docker build -t startercode-generator-bs .
# docker run -it --rm -v /data/dev/workspace/startercode-generator-bs:/code/startercode-generator-bs  --name startercode-generator-bs startercode-generator-bs
