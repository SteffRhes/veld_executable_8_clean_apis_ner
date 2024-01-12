FROM python:3.10.12
RUN pip install -U prefect==2.14.10
RUN useradd -u 1000 docker_user
RUN chown -R docker_user:docker_user /home/
USER docker_user

