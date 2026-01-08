import logging
import typing

from zeep.proxy import AsyncServiceProxy, ServiceProxy
from zeep.settings import Settings
from zeep.transports import AsyncTransport, Transport
from zeep.wsdl import Document

logger = logging.getLogger(__name__)


class Factory:
    def __init__(self, types, kind, namespace):
        self._method = getattr(types, "get_%s" % kind)

        if namespace in types.namespaces:
            self._ns = namespace
        else:
            self._ns = types.get_ns_prefix(namespace)

    def __getattr__(self, key):
        """Return the complexType or simpleType for the given localname.

        :rtype: zeep.xsd.ComplexType or zeep.xsd.AnySimpleType

        """
        return self[key]

    def __getitem__(self, key):
        """Return the complexType or simpleType for the given localname.

        :rtype: zeep.xsd.ComplexType or zeep.xsd.AnySimpleType

        """
        return self._method("{%s}%s" % (self._ns, key))


class Client:
    """The zeep Client.

    :param wsdl: Url/local WSDL location or preparsed WSDL Document
    :param wsse:
    :param transport: Custom transport class.
    :param service_name: The service name for the service binding. Defaults to
                         the first service in the WSDL document.
    :param port_name: The port name for the default binding. Defaults to the
                      first port defined in the service element in the WSDL
                      document.
    :param plugins: a list of Plugin instances
    :param settings: a zeep.Settings() object

    """

    _default_transport: typing.Union[Transport, AsyncTransport] = Transport

    def __init__(
        self,
        wsdl,
        wsse=None,
        transport=None,
        service_name=None,
        port_name=None,
        plugins=None,
        settings=None,
    ):
        if not wsdl:
            raise ValueError("No URL given for the wsdl")

        self.settings = settings or Settings()
        self.transport = (
            transport if transport is not None else self._default_transport()
        )
        if isinstance(wsdl, Document):
            self.wsdl = wsdl
        else:
            self.wsdl = Document(wsdl, self.transport, settings=self.settings)
        self.wsse = wsse
        self.plugins = plugins if plugins is not None else []

        self._default_service = None
        self._default_service_name = service_name
        self._default_port_name = port_name
        self._default_soapheaders = None

    @property
    def namespaces(self):
        return self.wsdl.types.prefix_map

    @property
    def service(self):
        """The default ServiceProxy instance

        :rtype: ServiceProxy

        """
        if self._default_service:
            return self._default_service

        self._default_service = self.bind(
            service_name=self._default_service_name, port_name=self._default_port_name
        )
        if not self._default_service:
            raise ValueError(
                "There is no default service defined. This is usually due to "
                "missing wsdl:service definitions in the WSDL"
            )
        return self._default_service

    def bind(
        self,
        service_name: typing.Optional[str] = None,
        port_name: typing.Optional[str] = None,
    ):
        """Create a new ServiceProxy for the given service_name and port_name.

        The default ServiceProxy instance (`self.service`) always referes to
        the first service/port in the wsdl Document.  Use this when a specific
        port is required.

        """
        if not self.wsdl.services:
            return

        service = self._get_service(service_name)
        port = self._get_port(service, port_name)
        return ServiceProxy(self, port.binding, **port.binding_options)

    def create_service(self, binding_name, address):
        """Create a new ServiceProxy for the given binding name and address.

        :param binding_name: The QName of the binding
        :param address: The address of the endpoint

        """
        try:
            binding = self.wsdl.bindings[binding_name]
        except KeyError:
            raise ValueError(
                "No binding found with the given QName. Available bindings "
                "are: %s" % (", ".join(self.wsdl.bindings.keys()))
            )
        return ServiceProxy(self, binding, address=address)

    def create_message(self, service, operation_name, *args, **kwargs):
        """Create the payload for the given operation.

        :rtype: lxml.etree._Element

        """
        envelope, http_headers = service._binding._create(
            operation_name, args, kwargs, client=self
        )
        return envelope

    def type_factory(self, namespace):
        """Return a type factory for the given namespace.

        Example::

            factory = client.type_factory('ns0')
            user = factory.User(name='John')

        :rtype: Factory

        """
        return Factory(self.wsdl.types, "type", namespace)

    def get_type(self, name):
        """Return the type for the given qualified name.

        :rtype: zeep.xsd.ComplexType or zeep.xsd.AnySimpleType

        """
        return self.wsdl.types.get_type(name)

    def get_element(self, name):
        """Return the element for the given qualified name.

        :rtype: zeep.xsd.Element

        """
        return self.wsdl.types.get_element(name)

    def set_ns_prefix(self, prefix, namespace):
        """Set a shortcut for the given namespace."""
        self.wsdl.types.set_ns_prefix(prefix, namespace)

    def set_default_soapheaders(self, headers):
        """Set the default soap headers which will be automatically used on
        all calls.

        Note that if you pass custom soapheaders using a list then you will
        also need to use that during the operations. Since mixing these use
        cases isn't supported (yet).

        """
        self._default_soapheaders = headers

    def _get_port(self, service, name):
        if name:
            port = service.ports.get(name)
            if not port:
                raise ValueError("Port not found")
        else:
            port = list(service.ports.values())[0]
        return port

    def _get_service(self, name: typing.Optional[str]) -> str:
        if name:
            service = self.wsdl.services.get(name)
            if not service:
                raise ValueError("Service not found")
        else:
            service = next(iter(self.wsdl.services.values()), None)
        return service

    def __enter__(self):
        return self

    def __exit__(self, exc_type=None, exc_value=None, traceback=None):
        if hasattr(self.transport, "close"):
            self.transport.close()


class AsyncClient(Client):
    _default_transport = AsyncTransport

    def bind(
        self,
        service_name: typing.Optional[str] = None,
        port_name: typing.Optional[str] = None,
    ):
        """Create a new ServiceProxy for the given service_name and port_name.

        The default ServiceProxy instance (`self.service`) always referes to
        the first service/port in the wsdl Document.  Use this when a specific
        port is required.

        """
        if not self.wsdl.services:
            return

        service = self._get_service(service_name)
        port = self._get_port(service, port_name)
        return AsyncServiceProxy(self, port.binding, **port.binding_options)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type=None, exc_value=None, traceback=None) -> None:
        await self.transport.aclose()


class CachingClient(Client):
    """Shortcut to create a caching client, for the lazy people.

    This enables the SqliteCache by default in the transport as was the default
    in earlier versions of zeep.

    """

    def __init__(self, *args, **kwargs):

        # Don't use setdefault since we want to lazily init the Transport cls
        from zeep.cache import SqliteCache

        kwargs["transport"] = kwargs.get("transport") or Transport(cache=SqliteCache())

        super().__init__(*args, **kwargs)
