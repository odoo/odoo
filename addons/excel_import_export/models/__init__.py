# Copyright 2019 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)
from . import styles
from . import common
from . import xlsx_export
from . import xlsx_import
from . import xlsx_template
from . import xlsx_report
from . import ir_report

#
#
# INSERT INTO "purchase_order_line" (
#     "id", "create_uid", "create_date",
#     "write_uid", "write_date", "date_planned",
#     "display_type", "name", "order_id",
#     "price_unit", "product_qty", "product_uom",
#     "sequence") VALUES (
#     nextval('purchase_order_line_id_seq'), 2, (now() at time zone 'UTC'),
#     2, (now() at time zone 'UTC'), '2020-10-05 09:39:28',
#     NULL, '[FURN_0269] Office Chair Black', 8,
#     '11111.00', '5.000', 1,
#     10)
