import copy
import itertools
import logging

logger = logging.getLogger(__name__)


class OperationProxy:
    def __init__(self, service_proxy, operation_name):
        self._proxy = service_proxy
        self._op_name = operation_name

    @property
    def __doc__(self):
        return str(self._proxy._binding._operations[self._op_name])

    def _merge_soap_headers(self, operation_soap_headers):
        default_headers = self._proxy._client._default_soapheaders

        # Merge the default _soapheaders with the passed _soapheaders
        if default_headers and operation_soap_headers:
            merged = copy.deepcopy(default_headers)
            if type(merged) != type(operation_soap_headers):
                raise ValueError("Incompatible soapheaders definition")

            if isinstance(operation_soap_headers, list):
                merged.extend(operation_soap_headers)
            else:
                merged.update(operation_soap_headers)
            return merged
        elif default_headers:
            return default_headers
        else:
            return operation_soap_headers

    def __call__(self, *args, **kwargs):
        """Call the operation with the given args and kwargs.

        :rtype: zeep.xsd.CompoundValue

        """
        soap_headers = self._merge_soap_headers(kwargs.get("_soapheaders"))
        if soap_headers:
            kwargs["_soapheaders"] = soap_headers

        return self._proxy._binding.send(
            self._proxy._client,
            self._proxy._binding_options,
            self._op_name,
            args,
            kwargs,
        )


class AsyncOperationProxy(OperationProxy):
    async def __call__(self, *args, **kwargs):
        """Call the operation with the given args and kwargs.

        :rtype: zeep.xsd.CompoundValue

        """
        kwargs["_soapheaders"] = self._merge_soap_headers(kwargs.get("_soapheaders"))

        return await self._proxy._binding.send_async(
            self._proxy._client,
            self._proxy._binding_options,
            self._op_name,
            args,
            kwargs,
        )


class ServiceProxy:
    def __init__(self, client, binding, **binding_options):
        self._client = client
        self._binding_options = binding_options
        self._binding = binding
        self._operations = {
            name: OperationProxy(self, name) for name in self._binding.all()
        }

    def __getattr__(self, key):
        """Return the OperationProxy for the given key.

        :rtype: OperationProxy()

        """
        return self[key]

    def __getitem__(self, key):
        """Return the OperationProxy for the given key.

        :rtype: OperationProxy()

        """
        try:
            return self._operations[key]
        except KeyError:
            raise AttributeError("Service has no operation %r" % key)

    def __iter__(self):
        """ Return iterator over the services and their callables. """
        return iter(self._operations.items())

    def __dir__(self):
        """ Return the names of the operations. """
        return list(itertools.chain(dir(super()), self._operations))


class AsyncServiceProxy(ServiceProxy):
    def __init__(self, client, binding, **binding_options):
        self._client = client
        self._binding_options = binding_options
        self._binding = binding
        self._operations = {
            name: AsyncOperationProxy(self, name) for name in self._binding.all()
        }
