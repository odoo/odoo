# https://github.com/gevent/gevent/issues/652 and 651
from gevent import monkey
monkey.patch_all()

import _import_wait # pylint:disable=import-error

assert _import_wait.x
