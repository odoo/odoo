# -*- coding: utf-8 -*-

from abc import ABCMeta, abstractmethod, abstractproperty
from odoo import fields, api, SUPERUSER_ID
from . import controllers
from . import models
from . import wizard
from . import report


def _load(cr, registry):
    '''安装模块后执行'''
    pass
  

def _uninstall(cr, registry):
    '''删除模块时执行'''
    pass
    