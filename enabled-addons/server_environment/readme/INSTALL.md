By itself, this module does little. See for instance the
`mail_environment` addon which depends on this one to allow configuring
the incoming and outgoing mail servers depending on the environment.

You can store your configuration values in a companion module called
`server_environment_files`. You can copy and customize the provided
`server_environment_files_sample` module for this purpose.
Alternatively, you can provide them in environment variables
`SERVER_ENV_CONFIG` and `SERVER_ENV_CONFIG_SECRET`.
