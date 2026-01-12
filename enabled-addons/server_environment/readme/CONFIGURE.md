To configure this module, you need to edit the main configuration file
of your instance, and add a directive called `running_env`. Commonly
used values are 'dev', 'test', 'production':

    [options]
    running_env=dev

Or set the `RUNNING_ENV` or `ODOO_STAGE` environment variable. If both all are set config file
will take the precedence on environment and `RUNNING_ENV` over `ODOO_STAGE`.

`ODOO_STAGE` is used for odoo.sh platform where we can't set `RUNNING_ENV`, possible
observed values are `production`, `staging` and `dev`

Values associated to keys containing 'passw' are only displayed in the
'dev' environment.

If you don't provide any value, test is used as a safe default.

You have several possibilities to set configuration values:

## server_environment_files

You can edit the settings you need in the `server_environment_files`
addon. The `server_environment_files_sample` can be used as an example:

- values common to all / most environments can be stored in the
  `default/` directory using the .ini file syntax;
- each environment you need to define is stored in its own directory and
  can override or extend default values;
- you can override or extend values in the main configuration file of
  your instance;

## Environment variable

You can define configuration in the environment variable
`SERVER_ENV_CONFIG` and/or `SERVER_ENV_CONFIG_SECRET`. The 2 variables
are handled the exact same way, this is only a convenience for the
deployment where you can isolate the secrets in a different, encrypted,
file. They are multi-line environment variables in the same configparser
format than the files. If you used options in
`server_environment_files`, the options set in the environment variable
override them.

The options in the environment variable are not dependent of
`running_env`, the content of the variable must be set accordingly to
the running environment.

Example of setup:

A public file, containing that will contain public variables:

    # These variables are not odoo standard variables,
    # they are there to represent what your file could look like
    export WORKERS='8'
    export MAX_CRON_THREADS='1'
    export LOG_LEVEL=info
    export LOG_HANDLER=":INFO"
    export DB_MAXCONN=5

    # server environment options
    export SERVER_ENV_CONFIG="
    [storage_backend.my_sftp]
    sftp_server=10.10.10.10
    sftp_login=foo
    sftp_port=22200
    directory_path=Odoo
    "

A second file which is encrypted and contains secrets:

    # This variable is not an odoo standard variable,
    # it is there to represent what your file could look like
    export DB_PASSWORD='xxxxxxxxx'
    # server environment options
    export SERVER_ENV_CONFIG_SECRET="
    [storage_backend.my_sftp]
    sftp_password=xxxxxxxxx
    "

**WARNING**

> my_sftp must match the name of the record. If you want something more
> reliable use server.env.techname.mixin and use tech_name field to
> reference records. See "USAGE".

## Default values

When using the `server.env.mixin` mixin, for each env-computed field, a
companion field `<field>_env_default` is created. This field is not
environment-dependent. It's a fallback value used when no key is set in
configuration files / environment variable.

When the default field is used, the field is made editable on Odoo.

Note: empty environment keys always take precedence over default fields

## Server environment integration

Read the documentation of the class
[models/server_env_mixin.py](models/server_env_mixin.py) and [models/server_env_tech_name_mixin.py]
(models/server_env_tech_name_mixin.py)
