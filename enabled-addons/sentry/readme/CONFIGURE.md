The following additional configuration options can be added to your Odoo
configuration file:

[TABLE]

Other [client
arguments](https://docs.sentry.io/platforms/python/configuration/) can
be configured by prepending the argument name with *sentry\_* in your
Odoo config file. Currently supported additional client arguments are:
`with_locals, max_breadcrumbs, release, environment, server_name, shutdown_timeout, in_app_include, in_app_exclude, default_integrations, dist, sample_rate, send_default_pii, http_proxy, https_proxy, request_bodies, debug, attach_stacktrace, ca_certs, propagate_traces, traces_sample_rate, auto_enabling_integrations`.

## Example Odoo configuration

Below is an example of Odoo configuration file with *Odoo Sentry*
options:

    [options]
    sentry_dsn = https://<public_key>:<secret_key>@sentry.example.com/<project id>
    sentry_enabled = true
    sentry_logging_level = warn
    sentry_exclude_loggers = werkzeug
    sentry_ignore_exceptions = odoo.exceptions.AccessDenied,
        odoo.exceptions.AccessError,odoo.exceptions.MissingError,
        odoo.exceptions.RedirectWarning,odoo.exceptions.UserError,
        odoo.exceptions.ValidationError,odoo.exceptions.Warning,
        odoo.exceptions.except_orm
    sentry_include_context = true
    sentry_environment = production
    sentry_release = 1.3.2
    sentry_odoo_dir = /home/odoo/odoo/
