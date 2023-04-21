# -*- coding: utf-8 -*-
"""Utilities for generating, parsing and checking XML/XSD files on top of the lxml.etree module."""

import logging
import requests
import zipfile
from io import BytesIO
from lxml import etree
import contextlib

from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)


class odoo_resolver(etree.Resolver):
    """Odoo specific file resolver that can be added to the XML Parser.

    It will search filenames in the ir.attachments
    """

    def __init__(self, env, prefix):
        super().__init__()
        self.env = env
        self.prefix = prefix

    def resolve(self, url, id, context):
        """Search url in ``ir.attachment`` and return the resolved content."""
        attachment_name = f'{self.prefix}.{url}' if self.prefix else url
        attachment = self.env['ir.attachment'].search([('name', '=', attachment_name)])
        if attachment:
            return self.resolve_string(attachment.raw, context)


def _check_with_xsd(tree_or_str, stream, env=None, prefix=None):
    """Check an XML against an XSD schema.

    This will raise a UserError if the XML file is not valid according to the
    XSD file.

    :param str | etree._Element tree_or_str: representation of the tree to be checked
    :param io.IOBase | str stream: the byte stream used to build the XSD schema.
        If env is given, it can also be the name of an attachment in the filestore
    :param odoo.api.Environment env: If it is given, it enables resolving the
        imports of the schema in the filestore with ir.attachments.
    :param str prefix: if given, provides a prefix to try when
        resolving the imports of the schema. e.g. prefix='l10n_cl_edi' will
        enable 'SiiTypes_v10.xsd' to be resolved to 'l10n_cl_edi.SiiTypes_v10.xsd'.
    """
    if not isinstance(tree_or_str, etree._Element):
        tree_or_str = etree.fromstring(tree_or_str)
    parser = etree.XMLParser()
    if env:
        parser.resolvers.add(odoo_resolver(env, prefix))
        if isinstance(stream, str) and stream.endswith('.xsd'):
            attachment = env['ir.attachment'].search([('name', '=', stream)])
            if not attachment:
                raise FileNotFoundError()
            stream = BytesIO(attachment.raw)
    xsd_schema = etree.XMLSchema(etree.parse(stream, parser=parser))
    try:
        xsd_schema.assertValid(tree_or_str)
    except etree.DocumentInvalid as xml_errors:
        raise UserError('\n'.join(str(e) for e in xml_errors.error_log))


def create_xml_node_chain(first_parent_node, nodes_list, last_node_value=None):
    """Generate a hierarchical chain of nodes.

    Each new node being the child of the previous one based on the tags contained
    in `nodes_list`, under the given node `first_parent_node`.

    :param etree._Element first_parent_node: parent of the created tree/chain
    :param iterable[str] nodes_list: tag names to be created
    :param str last_node_value: if specified, set the last node's text to this value
    :returns: the list of created nodes
    :rtype: list[etree._Element]
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

    :param etree._Element parent_node: parent of the created node
    :param str node_name: name of the created node
    :param str node_value: value of the created node (optional)
    :rtype: etree._Element
    """
    return create_xml_node_chain(parent_node, [node_name], node_value)[0]


def cleanup_xml_node(xml_node_or_string, remove_blank_text=True, remove_blank_nodes=True, indent_level=0, indent_space="  "):
    """Clean up the sub-tree of the provided XML node.

    If the provided XML node is of type:
    - etree._Element, it is modified in-place.
    - string/bytes, it is first parsed into an etree._Element
    :param xml_node_or_string (etree._Element, str): XML node (or its string/bytes representation)
    :param remove_blank_text (bool): if True, removes whitespace-only text from nodes
    :param remove_blank_nodes (bool): if True, removes leaf nodes with no text (iterative, depth-first, done after remove_blank_text)
    :param indent_level (int): depth or level of node within root tree (use -1 to leave indentation as-is)
    :param indent_space (str): string to use for indentation (use '' to remove all indentation)
    :returns (etree._Element): clean node, same instance that was received (if applicable)
    """
    xml_node = xml_node_or_string

    # Convert str/bytes to etree._Element
    if isinstance(xml_node, str):
        xml_node = xml_node.encode()  # misnomer: fromstring actually reads bytes
    if isinstance(xml_node, bytes):
        xml_node = etree.fromstring(xml_node)

    # Process leaf nodes iteratively
    # Depth-first, so any inner node may become a leaf too (if children are removed)
    def leaf_iter(parent_node, node, level):
        for child_node in node:
            leaf_iter(node, child_node, level if level < 0 else level + 1)

        # Indentation
        if level >= 0:
            indent = '\n' + indent_space * level
            if not node.tail or not node.tail.strip():
                node.tail = '\n' if parent_node is None else indent
            if len(node) > 0:
                if not node.text or not node.text.strip():
                    # First child's indentation is parent's text
                    node.text = indent + indent_space
                last_child = node[-1]
                if last_child.tail == indent + indent_space:
                    # Last child's tail is parent's closing tag indentation
                    last_child.tail = indent

        # Removal condition: node is leaf (not root nor inner node)
        if parent_node is not None and len(node) == 0:
            if remove_blank_text and node.text is not None and not node.text.strip():
                # node.text is None iff node.tag is self-closing (text='' creates closing tag)
                node.text = ''
            if remove_blank_nodes and not (node.text or ''):
                parent_node.remove(node)

    leaf_iter(None, xml_node, indent_level)
    return xml_node


def load_xsd_files_from_url(env, url, file_name=None, force_reload=False,
                            request_max_timeout=10, xsd_name_prefix='', xsd_names_filter=None, modify_xsd_content=None):
    """Load XSD file or ZIP archive. Save XSD files as ir.attachment.

    An XSD attachment is saved as {xsd_name_prefix}.{filename} where the filename is either the filename obtained
    from the URL or from the ZIP archive, or the `file_name` param if it is specified and a single XSD is being downloaded.
    A typical prefix is the calling module's name.

    For ZIP archives, XSD files inside it will be saved as attachments, depending on the provided list of XSD names.
    ZIP archive themselves are not saved.

    The XSD files content can be modified by providing the `modify_xsd_content` function as argument.
    Typically, this is used when XSD files depend on each other (with the schemaLocation attribute),
    but it can be used for any purpose.

    :param odoo.api.Environment env: environment of calling module
    :param str url: URL of XSD file/ZIP archive
    :param str file_name: used as attachment name if the URL leads to a single XSD, otherwise ignored
    :param bool force_reload: Deprecated.
    :param int request_max_timeout: maximum time (in seconds) before the request times out
    :param str xsd_name_prefix: if provided, will be added as a prefix to every XSD file name
    :param list | str xsd_names_filter: if provided, will only save the XSD files with these names
    :param func modify_xsd_content: function that takes the xsd content as argument and returns a modified version of it
    :rtype: odoo.api.ir.attachment | bool
    :return: every XSD attachment created/fetched or False if an error occurred (see warning logs)
    """
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

    content = response.content
    if not content:
        _logger.warning("The HTTP response from %s is empty (no content)", url)
        return False

    archive = None
    with contextlib.suppress(zipfile.BadZipFile):
        archive = zipfile.ZipFile(BytesIO(content))

    if archive is None:
        if modify_xsd_content:
            content = modify_xsd_content(content)
        if not file_name:
            file_name = f"{url.split('/')[-1]}"
            _logger.info("XSD name not provided, defaulting to %s", file_name)

        prefixed_xsd_name = f"{xsd_name_prefix}.{file_name}" if xsd_name_prefix else file_name
        fetched_attachment = env['ir.attachment'].search([('name', '=', prefixed_xsd_name)], limit=1)
        if fetched_attachment:
            _logger.info("Updating the content of ir.attachment with name: %s", prefixed_xsd_name)
            fetched_attachment.raw = content
            return fetched_attachment
        else:
            _logger.info("Saving XSD file as ir.attachment, with name: %s", prefixed_xsd_name)
            return env['ir.attachment'].create({
                'name': prefixed_xsd_name,
                'raw': content,
                'public': True,
            })

    saved_attachments = env['ir.attachment']
    for file_path in archive.namelist():
        if not file_path.endswith('.xsd'):
            continue

        file_name = file_path.rsplit('/', 1)[-1]

        if xsd_names_filter and file_name not in xsd_names_filter:
            _logger.info("Skipping file with name %s in ZIP archive", file_name)
            continue

        try:
            content = archive.read(file_path)
        except KeyError:
            _logger.warning("Failed to retrieve XSD file with name %s from ZIP archive", file_name)
            continue
        if modify_xsd_content:
            content = modify_xsd_content(content)

        prefixed_xsd_name = f"{xsd_name_prefix}.{file_name}" if xsd_name_prefix else file_name
        fetched_attachment = env['ir.attachment'].search([('name', '=', prefixed_xsd_name)], limit=1)
        if fetched_attachment:
            _logger.info("Updating the content of ir.attachment with name: %s", prefixed_xsd_name)
            fetched_attachment.raw = content
            saved_attachments |= fetched_attachment

        else:
            _logger.info("Saving XSD file as ir.attachment, with name: %s", prefixed_xsd_name)
            saved_attachments |= env['ir.attachment'].create({
                'name': prefixed_xsd_name,
                'raw': content,
                'public': True,
            })

    return saved_attachments


def validate_xml_from_attachment(env, xml_content, xsd_name, reload_files_function=None, prefix=None):
    """Try and validate the XML content with an XSD attachment.
    If the XSD attachment cannot be found in database, skip validation without raising.
    If the skip_xsd context key is truthy, skip validation.

    :param odoo.api.Environment env: environment of calling module
    :param xml_content: the XML content to validate
    :param xsd_name: the XSD file name in database
    :param reload_files_function: Deprecated.
    :return: the result of the function :func:`odoo.tools.xml_utils._check_with_xsd`
    """
    if env.context.get('skip_xsd', False):
        return

    prefixed_xsd_name = f"{prefix}.{xsd_name}" if prefix else xsd_name
    try:
        _logger.info("Validating with XSD...")
        _check_with_xsd(xml_content, prefixed_xsd_name, env, prefix)
        _logger.info("XSD validation successful!")
    except FileNotFoundError:
        _logger.info("XSD file not found, skipping validation")


def find_xml_value(xpath, xml_element, namespaces=None):
    element = xml_element.xpath(xpath, namespaces=namespaces)
    return element[0].text if element else None
