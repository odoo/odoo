# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models      # noqa
from . import report      # noqa

from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.tools.sql import column_exists, create_column

BATCH_SIZE = 10000


def _pre_init_hook(env):
    cr = env.cr
    for column in ('purchase_price', 'margin', 'margin_percent'):
        if not column_exists(cr, 'sale_order_line', column):
            create_column(cr, 'sale_order_line', column, 'float8')
    if not column_exists(cr, 'sale_order', 'margin'):
        create_column(cr, 'sale_order', 'margin', 'numeric')
    if not column_exists(cr, 'sale_order', 'margin_percent'):
        create_column(cr, 'sale_order', 'margin_percent', 'float8')


def _post_init_hook(env):
    def _recompute(model_name, ids, fnames):
        records = env[model_name].browse(ids)
        for fname in fnames:
            env.add_to_compute(records._fields[fname], records)  # mark as pending
        records._recompute_recordset(fnames)
        env.flush_all()
        env.invalidate_all()

    cutoff = fields.Datetime.now() - relativedelta(years=1)
    last_id = 0
    while True:
        # Batch in SQL (keyset pagination) so we never hold more than
        # BATCH_SIZE rows in memory, and skip already computed lines.
        env.cr.execute("""
            SELECT id, order_id
              FROM sale_order_line
             WHERE id > %s
               AND display_type IS NULL
               AND margin IS NULL
               AND create_date >= %s
             ORDER BY id
             LIMIT %s
        """, (last_id, cutoff, BATCH_SIZE))
        rows = env.cr.fetchall()
        if not rows:
            break
        last_id = rows[-1][0]
        line_ids = [row[0] for row in rows]
        order_ids = list({row[1] for row in rows})

        _recompute('sale.order.line', line_ids, ('purchase_price', 'margin', 'margin_percent'))
        _recompute('sale.order', order_ids, ('margin', 'margin_percent'))
