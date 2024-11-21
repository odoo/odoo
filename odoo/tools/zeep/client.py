import zeep

from decimal import Decimal
from datetime import date, datetime, timedelta
from requests import Response
from types import SimpleNamespace, FunctionType


TIMEOUT = 30
SERIALIZABLE_TYPES = (
    type(None), bool, int, float, str, bytes, tuple, list, dict, Decimal, date, datetime, timedelta, Response
)


class Client:
    """A wrapper for Zeep.Client

    * providing a simpler API to pass timeouts and session,
    * restricting its attributes to a few, most-commonly used accross Odoo's modules,
    * serializing the returned values of its methods.
    """
    def __init__(self, *args, **kwargs):
        transport = kwargs.setdefault('transport', zeep.Transport())
        # The timeout for loading wsdl and xsd documents.
        transport.load_timeout = kwargs.pop('timeout', None) or transport.load_timeout or TIMEOUT
        # The timeout for operations (POST/GET)
        transport.operation_timeout = kwargs.pop('operation_timeout', None) or transport.operation_timeout or TIMEOUT
        # The `requests.session` used for HTTP requests
        transport.session = kwargs.pop('session', None) or transport.session

        client = zeep.Client(*args, **kwargs)

        self.__obj = client
        self.__service = None

    @classmethod
    def __serialize_object(cls, obj):
        if isinstance(obj, list):
            return [cls.__serialize_object(sub) for sub in obj]
        if isinstance(obj, (dict, zeep.xsd.valueobjects.CompoundValue)):
            result = SerialProxy(**{key: cls.__serialize_object(obj[key]) for key in obj})
            return result
        if type(obj) in SERIALIZABLE_TYPES:
            return obj
        raise ValueError(f'{obj} is not serializable')

    @classmethod
    def __serialize_object_wrapper(cls, method):
        def wrapper(*args, **kwargs):
            return cls.__serialize_object(method(*args, **kwargs))
        return wrapper

    @property
    def service(self):
        if not self.__service:
            self.__service = ReadOnlyMethodNamespace(**{
                key: self.__serialize_object_wrapper(operation)
                for key, operation in self.__obj.service._operations.items()
            })
        return self.__service

    def type_factory(self, namespace):
        types = self.__obj.wsdl.types
        namespace = namespace if namespace in types.namespaces else types.get_ns_prefix(namespace)
        documents = types.documents.get_by_namespace(namespace, fail_silently=True)
        types = {
            key[len(f'{{{namespace}}}'):]: type_
            for document in documents
            for key, type_ in document._types.items()
        }
        return ReadOnlyMethodNamespace(**{key: self.__serialize_object_wrapper(type_) for key, type_ in types.items()})

    def get_type(self, name):
        return self.__serialize_object_wrapper(self.__obj.wsdl.types.get_type(name))

    def create_service(self, binding_name, address):
        service = self.__obj.create_service(binding_name, address)
        return ReadOnlyMethodNamespace(**{
            key: self.__serialize_object_wrapper(operation)
            for key, operation in service._operations.items()
        })

    def bind(self, service_name, port_name):
        service = self.__obj.bind(service_name, port_name)
        operations = {
            key: self.__serialize_object_wrapper(operation)
            for key, operation in service._operations.items()
        }
        operations['_binding_options'] = service._binding_options
        return ReadOnlyMethodNamespace(**operations)


class ReadOnlyMethodNamespace(SimpleNamespace):
    """A read-only attribute-based namespace not prefixed by `_` and restricted to functions.

    By default, `types.SympleNamespace` doesn't implement `__setitem__` and `__delitem__`,
    no need to implement them to ensure the read-only property of this class.
    """
    def __init__(self, **kwargs):
        assert all(
            (not key.startswith('_') and isinstance(value, FunctionType))
            or
            (key == '_binding_options' and isinstance(value, dict))
            for key, value in kwargs.items()
        )
        super().__init__(**kwargs)

    def __getitem__(self, key):
        return self.__dict__[key]

    def __setattr__(self, key, value):
        raise NotImplementedError

    def __delattr__(self, key):
        raise NotImplementedError


class SerialProxy(SimpleNamespace):
    """An attribute-based namespace not prefixed by `_` and restricted to few types.

    It pretends to be a zeep `CompoundValue` so zeep.helpers.serialize_object threats it as such.

    `__getitem__` and `__delitem__` are supported, but `__setitem__` is prevented,
    e.g.
    ```py
    proxy = SerialProxy(foo='foo')
    proxy.foo  # Allowed
    proxy['foo']  # Allowed
    proxy.foo = 'bar'  # Allowed
    proxy['foo'] = 'bar'  # Prevented
    del proxy.foo  # Allowed
    del proxy['foo']  # Allowed
    ```
    """

    # Pretend to be a CompoundValue so zeep can serialize this when sending a request with this object in the payload
    # https://stackoverflow.com/a/42958013
    # https://github.com/mvantellingen/python-zeep/blob/a65b4363c48b5c3f687b8df570bcbada8ba66b9b/src/zeep/helpers.py#L15
    @property
    def __class__(self):
        return zeep.xsd.valueobjects.CompoundValue

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            self.__check(key, value)
        super().__init__(**kwargs)

    def __setattr__(self, key, value):
        self.__check(key, value)
        return super().__setattr__(key, value)

    def __getitem__(self, key):
        return self.__getattribute__(key)

    # Not required as SimpleNamespace doesn't implement it by default, but this makes it explicit.
    def __setitem__(self, key, value):
        raise NotImplementedError

    def __delitem__(self, key):
        self.__delattr__(key)

    def __iter__(self):
        return iter(self.__dict__)

    def __repr__(self):
        return repr(self.__dict__)

    def __str__(self):
        return str(self.__dict__)

    def keys(self):
        return self.__dict__.keys()

    def values(self):
        return self.__dict__.values()

    def items(self):
        return self.__dict__.items()

    @classmethod
    def __check(cls, key, value):
        assert not key.startswith('_') or key.startswith('_value_')
        assert type(value) in SERIALIZABLE_TYPES + (SerialProxy,)
