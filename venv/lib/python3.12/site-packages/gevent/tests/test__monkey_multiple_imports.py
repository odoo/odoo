# https://github.com/gevent/gevent/issues/615
# Under Python 3, with its use of importlib,
# if the monkey patch is done when the importlib import lock is held
# (e.g., during recursive imports) we could fail to release the lock.
# This is surprisingly common.
__import__('_import_import_patch')
