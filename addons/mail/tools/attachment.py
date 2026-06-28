# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re


def extract_attachment_ids_from_html(html):
    """ Return the set of attachments ids present as link in the html. """
    return {int(link) for link in re.findall(r'/web/(?:content|image)/([0-9]+)', html)}
