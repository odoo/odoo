import logging
import sys
import os

import odoo

from .command import Command, main

from . import cloc
from . import upgrade_code
from . import deploy
from . import scaffold
from . import server
from . import shell
from . import start
from . import populate
from . import tsconfig
from . import neutralize
from . import obfuscate
from . import genproxytoken
from . import db
