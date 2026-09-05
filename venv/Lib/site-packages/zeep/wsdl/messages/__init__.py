"""
    zeep.wsdl.messages
    ~~~~~~~~~~~~~~~~~~

    The messages are responsible for serializing and deserializing

    .. inheritance-diagram::
            zeep.wsdl.messages.soap.DocumentMessage
            zeep.wsdl.messages.soap.RpcMessage
            zeep.wsdl.messages.http.UrlEncoded
            zeep.wsdl.messages.http.UrlReplacement
            zeep.wsdl.messages.mime.MimeContent
            zeep.wsdl.messages.mime.MimeXML
            zeep.wsdl.messages.mime.MimeMultipart
       :parts: 1

"""
from .http import *  # noqa
from .mime import *  # noqa
from .soap import *  # noqa
