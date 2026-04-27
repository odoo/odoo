# Part of Odoo. See LICENSE file for full copyright and licensing details.

from zeep import xsd

from odoo.tools.zeep import client


class Client(client.Client):
    """This class is made to loosen a bit the restrictions of the original class
    to make it usable with really old api like the one of monster.
    """

    @classmethod
    def __serialize_object(cls, obj):
        if isinstance(obj, list):
            return [cls.__serialize_object(sub) for sub in obj]
        if isinstance(obj, (dict, xsd.valueobjects.CompoundValue)):
            result = SerialProxy(**{key: cls.__serialize_object(obj[key]) for key in obj})
            return result
        if type(obj) in client.SERIALIZABLE_TYPES:
            return obj
        raise ValueError(f'{obj} is not serializable')


class SerialProxy(client.SerialProxy):
    """This class is made to loosen a bit the restrictions of the original class
    to make it usable with really old api like the one of monster.
    """

    @classmethod
    def __check(cls, key, value):
        assert not key.startswith('_') or key == '_value_1'
        assert type(value) in client.SERIALIZABLE_TYPES + (SerialProxy,)
