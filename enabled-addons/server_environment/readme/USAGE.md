You can include a mixin in your model and configure the env-computed
fields by an override of `_server_env_fields`.

    class StorageBackend(models.Model):
        _name = "storage.backend"
        _inherit = ["storage.backend", "server.env.mixin"]

        @property
        def _server_env_fields(self):
            return {"directory_path": {}}

Read the documentation of the class and methods in
[models/server_env_mixin.py](models/server_env_mixin.py).

If you want to have a technical name to reference:

    class StorageBackend(models.Model):
        _name = "storage.backend"
        _inherit = ["storage.backend", "server.env.techname.mixin"]

        [...]
