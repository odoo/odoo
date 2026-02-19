# Copyright 2016 ACSONE SA/NV (<http://acsone.eu>)
# Copyright 2016 Akretion (<http://akretion.com>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).


class DataError(Exception):
    def __init__(self, name, msg):
        super().__init__()
        self.name = name
        self.msg = msg

    def __repr__(self):
        return f"{self.__class__.__name__}({repr(self.name)})"


class NameDataError(DataError):
    pass
