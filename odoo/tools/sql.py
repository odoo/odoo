# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from functools import partial


def drop_view_if_exists(cr, viewname):
    cr.execute("DROP view IF EXISTS %s CASCADE" % (viewname,))
    cr.commit()

def escape_psql(to_escape):
    return to_escape.replace('\\', r'\\').replace('%', '\%').replace('_', '\_')

def pg_varchar(size=0):
    """ Returns the VARCHAR declaration for the provided size:

    * If no size (or an empty or negative size is provided) return an
      'infinite' VARCHAR
    * Otherwise return a VARCHAR(n)

    :type int size: varchar size, optional
    :rtype: str
    """
    if size:
        if not isinstance(size, int):
            raise ValueError("VARCHAR parameter should be an int, got %s" % type(size))
        if size > 0:
            return 'VARCHAR(%d)' % size
    return 'VARCHAR'

def reverse_order(order):
    """ Reverse an ORDER BY clause """
    items = []
    for item in order.split(','):
        item = item.lower().split()
        direction = 'asc' if item[1:] == ['desc'] else 'desc'
        items.append('%s %s' % (item[0], direction))
    return ', '.join(items)


def default_sequence(self=None, field=None, reverse_order=False):
    """
        Returns the default value that ``field`` should take for
        a new record to be added at the correct position.

        This assumes the model is actually ordered by that field,
        otherwise it might not return the expected value.

        This doesn't handle concurrent or batch create/update/delete operations,
        which have to be handled by the caller (usually a view) if necessary.

        :param field: string with the name of the sequence field.
            The first field in ``self._order`` will be taken if left empty.
            If specified, it must be present in ``self._order``.
            It cannot be ``id``.

        :param reverse_order: boolean: Set ``True`` if the order specified in
            ``self._order`` for the ``field`` has to be reversed.

            Setting ``sequence_reverse_order``in the context
                will override the value of reverse_order.

        :return: the default value
        :rtype: int
    """
    if self is None:
        return partial(default_sequence, field=field, reverse_order=reverse_order)

    descending = None

    for clause in self._order.split(','):
        clause = clause.lower().split()
        if not field:
            field = clause[0]
        if field == clause[0]:
            if clause[0] == 'id':
                raise Exception("Default sequence should not be used on the ID field.")
            descending = clause[1:] == ['desc']
            break

    if descending is None:
        raise Exception("Default sequence should be used only on fields present in _order.")

    if self.env.context.get('sequence_reverse_order', reverse_order):
        descending = not descending
    cr = self.env.cr
    if descending:
        cr.execute("SELECT min({})-1 FROM {}".format(field, self._table))
    else:
        cr.execute("SELECT max({})+1 FROM {}".format(field, self._table))
    row = cr.fetchone()
    return row[0] if row else 0
