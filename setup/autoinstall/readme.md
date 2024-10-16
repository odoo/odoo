This folder contains the tools to setup an environment able to run Odoo.

The main goal is to setup an development environment on a debian like system, even if it could also be used for production.

This command can be tested in a minimal docker image as described in tests/Dockerfile using the command:

`docker build -t odoo-autoinstall -f tests/Dockerfile .`


The docker image can be started in interactive mode using

`docker run -ti --rm -v $(pwd):/home/odoo/autoinstall:ro -v ~/.ssh:/home/odoo/.ssh:ro  -w /home/odoo/autoinstall odoo-autoinstall`

Note that the scripts requires ssh key linked to a github account in order to clone repositories using ssh and not https

Then, the command to setup the environment is:

`./autoinstall.py`

To have a full dev version, without question (except passwords when needed)

`./autoinstall.py -ay`

