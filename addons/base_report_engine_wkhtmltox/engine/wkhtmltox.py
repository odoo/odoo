

class WkHtmlToX():
    def __init__(self):
        ...

    @staticmethod
    def _construct_args(*args, **kwargs):
        extra_args = args
        for kwarg_name, kwarg_value in kwargs.items():
            extra_args += (f"--{kwarg_name}", str(kwarg_value))
        return extra_args

    def _run(self, mode, *args): ...


    def print(self, *args, **kwargs): ...

    def render(self, *args, **kwargs): ...
