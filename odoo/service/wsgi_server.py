import warnings
import odoo.http


def application(environ, start_response):

    warnings.warn("The WSGI application entrypoint moved from "
                  "odoo.service.wsgi_server.application to odoo.http.root "
                  "in 15.3.",
                  DeprecationWarning, stacklevel=1)
    return odoo.http.root(environ, start_response)
