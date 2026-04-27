import csv
import logging

from odoo import tools

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    csv_path = "l10n_mx_edi_stock/data/product.unspsc.code.csv"

    with tools.misc.file_open(csv_path, "r") as csv_file:
        reader = csv.reader(csv_file)
        if not reader:
            _logger.warning("The CSV file product.unspsc.code.csv wasn't found.")
            return
        next(reader)
        data = [(row[0], row[1]) for row in reader]
        query = """
            UPDATE product_unspsc_code p
            SET l10n_mx_edi_hazardous_material = raw.hazardous_value
            FROM (
                VALUES %s
            ) AS raw(full_xml_id, hazardous_value)
            JOIN LATERAL (
                SELECT
                    (regexp_split_to_array(raw.full_xml_id, '\\.'))[1] AS module,
                    (regexp_split_to_array(raw.full_xml_id, '\\.'))[2] AS name
            ) AS v ON true
            JOIN ir_model_data imd
                ON imd.module = v.module
            AND imd.name = v.name
            WHERE p.id = imd.res_id
        """
        cr.execute_values(query, data)
