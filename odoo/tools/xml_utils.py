# -*- coding: utf-8 -*-
"""Utilities for generating, parsing and checking XML/XSD files on top of the lxml.etree module."""

import base64
import logging
import requests
from io import BytesIO
from lxml import etree

from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)


class odoo_resolver(etree.Resolver):
    """Odoo specific file resolver that can be added to the XML Parser.

    It will search filenames in the ir.attachments
    """

    def __init__(self, env):
        super().__init__()
        self.env = env

    def resolve(self, url, id, context):
        """Search url in ``ir.attachment`` and return the resolved content."""
        attachment = self.env['ir.attachment'].search([('name', '=', url)])
        if attachment:
            return self.resolve_string(base64.b64decode(attachment.datas), context)


def _check_with_xsd(tree_or_str, stream, env=None):
    """Check an XML against an XSD schema.

    This will raise a UserError if the XML file is not valid according to the
    XSD file.
    :param tree_or_str (etree, str): representation of the tree to be checked
    :param stream (io.IOBase, str): the byte stream used to build the XSD schema.
        If env is given, it can also be the name of an attachment in the filestore
    :param env (odoo.api.Environment): If it is given, it enables resolving the
        imports of the schema in the filestore with ir.attachments.
    """
    if not isinstance(tree_or_str, etree._Element):
        tree_or_str = etree.fromstring(tree_or_str)
    parser = etree.XMLParser()
    if env:
        parser.resolvers.add(odoo_resolver(env))
        if isinstance(stream, str) and stream.endswith('.xsd'):
            attachment = env['ir.attachment'].search([('name', '=', stream)])
            if not attachment:
                raise FileNotFoundError()
            stream = BytesIO(base64.b64decode(attachment.datas))
    xsd_schema = etree.XMLSchema(etree.parse(stream, parser=parser))
    try:
        xsd_schema.assertValid(tree_or_str)
    except etree.DocumentInvalid as xml_errors:
        raise UserError('\n'.join(str(e) for e in xml_errors.error_log))


def create_xml_node_chain(first_parent_node, nodes_list, last_node_value=None):
    """Generate a hierarchical chain of nodes.

    Each new node being the child of the previous one based on the tags contained
    in `nodes_list`, under the given node `first_parent_node`.
    :param first_parent_node (etree._Element): parent of the created tree/chain
    :param nodes_list (iterable<str>): tag names to be created
    :param last_node_value (str): if specified, set the last node's text to this value
    :returns (list<etree._Element>): the list of created nodes
    """
    res = []
    current_node = first_parent_node
    for tag in nodes_list:
        current_node = etree.SubElement(current_node, tag)
        res.append(current_node)

    if last_node_value is not None:
        current_node.text = last_node_value
    return res


def create_xml_node(parent_node, node_name, node_value=None):
    """Create a new node.

    :param parent_node (etree._Element): parent of the created node
    :param node_name (str): name of the created node
    :param node_value (str): value of the created node (optional)
    :returns (etree._Element):
    """
    return create_xml_node_chain(parent_node, [node_name], node_value)[0]


def load_xsd_from_url(env, url, xsd_code, force_reload=False, request_max_timeout=10):
    """Load XSD file or ZIP archive and save it as ir.attachment.

    If the XSD file/archive has already been saved in database, then just return the attachment.
    In such a case, the attachment content can also be updated by force if desired.

    The ir.attachment file name is of the following format:

    *<xsd_code>.xsd_cached_<short_url>*

    Where *short_url* is the last part of the provided URL (each part is separated by a slash),
    with every dot replaced by an underscore.

    This format is used to ensure the uniqueness of the attachment, based on a special code (module name for instance).

    :param odoo.api.Environment env: environment of calling module
    :param str url: URL of XSD file/ZIP archive
    :param str xsd_code: the code (prefix) given to the XSD attachment name in order to index the attachments.
    :param bool force_reload: if True, reload the attachment from URL, even if it is already cached
    :param int request_max_timeout: maximum time (in seconds) before the request times out
    :rtype: odoo.api.ir.attachment
    :return: the attachment or False if an error occurred (see warning logs)
    """
    if not url.endswith(('.xsd', '.zip')):
        _logger.warning("The given URL (%s) needs to lead to an XSD file or a ZIP archive", url)
        return False

    short_url = url.split('/')[-1].replace('.', '_')
    xsd_file_name = '%s.xsd_cached_%s' % (xsd_code, short_url)

    fetched_attachment = env['ir.attachment'].search([('name', '=', xsd_file_name)])
    if fetched_attachment and not force_reload:
        _logger.info("Retrieved attachment from database, with name: %s", fetched_attachment.name)
        return fetched_attachment

    try:
        _logger.info("Fetching file/archive from given URL: %s", url)
        response = requests.get(url, timeout=request_max_timeout)
        response.raise_for_status()
    except requests.exceptions.HTTPError as error:
        _logger.warning('HTTP error: %s with the given URL: %s', error, url)
        return False
    except requests.exceptions.ConnectionError as error:
        _logger.warning('Connection error: %s with the given URL: %s', error, url)
        return False
    except requests.exceptions.Timeout as error:
        _logger.warning('Request timeout: %s with the given URL: %s', error, url)
        return False

    if fetched_attachment:
        _logger.info("Updating the content of ir.attachment with name: %s", xsd_file_name)
        fetched_attachment.update({
            'raw': response.content
        })
        return fetched_attachment

    _logger.info("Saving XSD file as ir.attachment, with name: %s", xsd_file_name)
    return env['ir.attachment'].create({
        'name': xsd_file_name,
        'raw': response.content,
        'public': True,
    })
