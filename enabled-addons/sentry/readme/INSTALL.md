The module can be installed just like any other Odoo module, by adding
the module's directory to Odoo *addons_path*. In order for the module to
correctly wrap the Odoo WSGI application, it also needs to be loaded as
a server-wide module. This can be done with the `server_wide_modules`
parameter in your Odoo config file or with the `--load` command-line
parameter.

This module additionally requires the sentry-sdk Python package to be
available on the system. It can be installed using pip:

    pip install sentry-sdk
