# -*- encoding: utf-8 -*-

__name__ = "Convert jobs pickled func to bytea"


def migrate(cr, version):
    if not version:
        return
    cr.execute("ALTER TABLE queue_job ALTER func "
               "TYPE bytea USING convert_to(func, 'LATIN1') ")
