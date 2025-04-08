# Part of Odoo. See LICENSE file for full copyright and licensing details.

from itertools import islice
from lxml import etree

from odoo.tools import split_every


def _split_table(tree, max_rows):
    """
    Walks through the etree and splits tables with more than max_rows rows into
    multiple tables with max_rows rows.
    This function is needed because wkhtmltopdf has a exponential processing
    time growth when processing tables with many rows. This function is a
    workaround for this problem.
    :param tree: The etree to process
    :param max_rows: The maximum number of rows per table
    """
    for table in list(tree.iter('table')):
        prev = table
        for rows in islice(split_every(max_rows, table), 1, None):
            sibling = etree.Element('table', attrib=table.attrib)
            sibling.extend(rows)
            prev.addnext(sibling)
            prev = sibling
