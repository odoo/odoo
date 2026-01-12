This module provides a way to define an environment in the main Odoo
configuration file and to read some configurations from files depending
on the configured environment: you define the environment in the main
configuration file, and the values for the various possible environments
are stored in the `server_environment_files` companion module.

The `server_environment_files` module is optional, the values can be set
using an environment variable with a fallback on default values in the
database.

The configuration read from the files are visible under the
Configuration menu. If you are not in the 'dev' environment you will not
be able to see the values contained in the defined secret keys (by
default : '*passw*', '*key*', '*secret*' and '*token*').
