FROM python:3.10.12
RUN useradd -u 1000 docker_user
RUN chown -R docker_user:docker_user /home/
USER docker_user

