# ruff: noqa: PLC0415

_soap_clients = {}


def new_get_soap_client(wsdlurl, timeout=30):
    # stdnum library does not set the timeout for the zeep Transport class correctly
    # (timeout is to fetch the wsdl and operation_timeout is to perform the call),
    # requiring us to monkey patch the get_soap_client function.
    # Can be removed when https://github.com/arthurdejong/python-stdnum/issues/444 is
    # resolved and the version of the dependency is updated.
    # The code is a copy of the original apart for the line related to the Transport class.
    # This was done to keep the code as similar to the original and to reduce the possibility
    # of introducing import errors, even though some imports are not in the requirements.
    # See https://github.com/odoo/odoo/pull/173359 for a more thorough explanation.
    if (wsdlurl, timeout) not in _soap_clients:
        try:
            from zeep.transports import Transport
            transport = Transport(operation_timeout=timeout, timeout=timeout)  # operational_timeout added here
            from zeep import CachingClient
            client = CachingClient(wsdlurl, transport=transport).service
        except ImportError:
            # fall back to non-caching zeep client
            try:
                from zeep import Client
                client = Client(wsdlurl, transport=transport).service
            except ImportError:
                # other implementations require passing the proxy config
                try:
                    from urllib import getproxies
                except ImportError:
                    from urllib.request import getproxies
                # fall back to suds
                try:
                    from suds.client import Client
                    client = Client(
                        wsdlurl, proxy=getproxies(), timeout=timeout).service
                except ImportError:
                    # use pysimplesoap as last resort
                    try:
                        from pysimplesoap.client import SoapClient
                        client = SoapClient(
                            wsdl=wsdlurl, proxy=getproxies(), timeout=timeout)
                    except ImportError:
                        raise ImportError(
                            'No SOAP library (such as zeep) found')
        _soap_clients[(wsdlurl, timeout)] = client
    return _soap_clients[(wsdlurl, timeout)]


def patch_module():
    try:
        from stdnum import util
    except ImportError:
        return  # nothing to patch

    util.get_soap_client = new_get_soap_client
