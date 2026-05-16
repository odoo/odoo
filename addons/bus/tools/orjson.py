try:
    import orjson

    def dumps(value):
        return orjson.dumps(value)

    def loads(value):
        return orjson.loads(value)
except ImportError:
    import json

    def dumps(value):
        return json.dumps(value, separators=(",", ":")).encode()

    def loads(value):
        return json.loads(value)
