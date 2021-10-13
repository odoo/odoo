class PosLoader:
    def __init__(self):
        self._loaders = {}
        self._sorted_models = []

    def _find_index(self, model):
        return next((i for i, _model in enumerate(self._sorted_models) if _model == model), -1)

    def info(self, model, requires=None, before=None, after=None):
        def wrapper(method):
            model_index = self._find_index(model)
            after_index = self._find_index(after) if after else -1
            before_index = self._find_index(before) if before else -1
            if model_index == -1:
                self._sorted_models.append(model)
            elif after_index > -1:
                self._sorted_models.insert(after_index + 1, model)
            elif before_index > -1:
                self._sorted_models.insert(before_index, model)

            if not model in self._loaders:
                self._loaders[model] = {'model': model}
            self._loaders[model]['info'] = {
                'method': method.__name__,
                'requires': requires or [],
            }
            return method
        return wrapper

    def load(self, model, requires=None):
        def wrapper(method):
            self._loaders[model]['load'] = {
                'method': method.__name__,
                'requires': requires or [],
            }
            return method
        return wrapper

    def post(self, model, requires=None):
        def wrapper(method):
            self._loaders[model]['post'] = {
                'method': method.__name__,
                'requires': requires or [],
            }
            return method
        return wrapper
