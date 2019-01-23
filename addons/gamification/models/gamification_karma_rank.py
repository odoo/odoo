# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import Forbidden


class KarmaError(Forbidden):
    """ Karma-related error, used for forum and posts. """
    pass
