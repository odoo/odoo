FROM xdevelsistemas/debian-env:python-dev-env
MAINTAINER xdevel <clayton@xdevel.com.br>


ENV ODOO_VERSION 9.0
ENV ODOO_RELEASE xdevel-release




#create odoo user
RUN groupadd -r odoo && useradd -r -g odoo odoo  \
    && gpasswd -a odoo fuse


# Copy entrypoint script and Odoo configuration file
ADD . /home/odoo/odoo
WORKDIR /home/odoo/odoo
RUN chown -R odoo:odoo /home/odoo \ 
	&& pip install -r requirements.txt

# Mount /var/lib/odoo to allow restoring filestore and /mnt/extra-addons for users addons
#RUN mkdir -p /mnt/extra-addons \
#        && chown -R odoo /mnt/extra-addons
#VOLUME ["/var/lib/odoo","/mnt/extra-addons"]

# Expose Odoo services
EXPOSE 8069 8071

# Set default user when running the container
USER odoo


ENTRYPOINT ["bash","/home/odoo/odoo/docker-entrypoint.sh"]

CMD ["/home/odoo/odoo/openerp-server"]
