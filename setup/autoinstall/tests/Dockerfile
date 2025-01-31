# This file is used to create a docker image for testing purposes,
# containing the strict minimal depenencies to run autoinstall
FROM ubuntu:noble

RUN apt-get update && apt-get install -y \
    sudo \
    curl \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

ARG USER=odoo
RUN usermod --login ${USER} --move-home --home /home/${USER} ubuntu
RUN sudo adduser ${USER} sudo
# Set password for the user to x for easy testing
RUN echo "${USER}:x" | chpasswd

# bad practice, but easier for testing purposes
RUN apt-get update 

USER ${USER}
