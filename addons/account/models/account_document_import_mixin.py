from contextlib import contextmanager
from copy import deepcopy
import difflib
import io
import itertools
import logging
from lxml import etree
from markupsafe import Markup
from struct import error as StructError

from odoo import api, models, modules
from odoo.exceptions import RedirectWarning
from odoo.tools import groupby
from odoo.tools.mimetypes import guess_mimetype
from odoo.tools.pdf import OdooPdfFileReader, PdfReadError

_logger = logging.getLogger(__name__)


def _can_commit():
    """ Helper to know if we can commit the current transaction or not.

    :returns: True if commit is acceptable, False otherwise.
    """
    return not modules.module.current_test


@contextmanager
def rollbackable_transaction(cr):
    """ A savepoint-less commit/rollback context manager.

    Commits the cursor, then executes the code inside the context manager, then tries to commit again.
    Rolls the cursor back if an exception was raised.

    ⚠️ Because this method commits the cursor, try to:
    (1) do as much work as possible before calling this method, and
    (2) avoid triggering a SerializationError later in the request. If a SerializationError happens,
        `retrying` will cause the whole request to be retried, which may cause some things
        to be duplicated. That may be more or less undesirable, depending on what you're doing.
        (This method will gracefully handle SerializationErrors caused within the context manager.)

    :raise: an Exception if an error was caught and the transaction was rolled back.
    """
    if not _can_commit():
        yield
        return

    # We start by committing so that if we do a rollback in the except block, we don't lose all the progress that
    # was done before this method was called. If a SerializationError occurs here, no problem - nothing will be
    # committed and the whole request will be restarted by the `retrying` mechanism.
    cr.commit()
    try:
        # This may trigger both database errors (e.g. SQL constraints)
        # and Python exceptions (e.g. UserError / ValidationError).
        # In both cases, we want to roll back and log an error on the invoice.
        yield

        # Commit in order to trigger any SerializationError right now, while we can still rollback.
        cr.commit()

    except Exception:
        cr.rollback()
        raise


def split_etree_on_tag(tree, tag):
    """ Split an etree that has multiple instances of a given tag into multiple trees
    that each have a single instance of the tag.

    That is,
    treeA = etree.fromstring('''
        <A>
            <B>Some header</B>
            <C>First</C>
            <C>Second</C>
        </A>
    ''')

    gets split by `split_etree_on_tag(etree_A, 'C')` into

    <A>
        <B>Some header</B>
        <C>First</C>
    </A>

    and

    <A>
        <B>Some header</B>
        <C>Second</C>
    </A>
    """
    tree = deepcopy(tree)
    nodes_to_split = tree.findall(f'.//{tag}')

    # Remove all nodes with the tag
    parent_node = nodes_to_split[0].getparent()
    for node in nodes_to_split:
        parent_node.remove(node)

    # Create a new tree for each node
    trees = []
    for node in nodes_to_split:
        parent_node.append(node)
        trees.append(deepcopy(tree))
        parent_node.remove(node)
    return trees


def extract_pdf_embedded_files(filename, content):
    with io.BytesIO(content) as buffer:
        try:
            pdf_reader = OdooPdfFileReader(buffer, strict=False)
        except Exception as e:  # noqa: BLE001
            # Malformed pdf
            _logger.info('Error when reading the pdf file "%s": %s', filename, e)
            return []

        try:
            return list(pdf_reader.getAttachments())
        except (NotImplementedError, StructError, PdfReadError) as e:
            _logger.warning("Unable to access the attachments of %s. Tried to decrypt it, but %s.", filename, e)
            return []


class AccountDocumentImportMixin(models.AbstractModel):
    _name = 'account.document.import.mixin'
    _description = "Business document import mixin"

    @api.model
    def _create_records_from_attachments(self, attachments, grouping_method=None):
        """ For each attachment, create a corresponding record, and attempt to decode the
            attachment on the record.

            Some attachments (e.g. in some EDI formats) may contain multiple business
            documents; in that case, we attempt to separate them and create a new record for
            each business document.

            ⚠️ Because this method commits the cursor, try to:
            (1) do as much work as possible before calling this method, and
            (2) avoid triggering a SerializationError later in the request. If a SerializationError happens,
                `retrying` will cause the whole request to be retried, which may cause some things
                to be duplicated. That may be more or less undesirable, depending on what you're doing.
        """
        if grouping_method is None:
            grouping_method = self._group_files_data_by_origin_attachment

        files_data = self._to_files_data(attachments)

        # Extract embedded attachments
        files_data.extend(self._unwrap_attachments(files_data))

        # Perform a grouping to determine how many invoices to create
        file_data_groups = grouping_method(files_data)

        records = self.create([{}] * len(file_data_groups))
        for record, file_data_group in zip(records, file_data_groups):
            attachment_records = self._from_files_data(file_data_group)
            attachment_records.write({
                'res_model': record._name,
                'res_id': record.id,
            })
            record.message_post(
                body=self.env._("This document was created from the following attachment(s)."),
                attachment_ids=attachment_records.ids
            )

        # Call _extend_with_attachments at the end, because it commits the transaction.
        for record, file_data_group in zip(records, file_data_groups):
            record._extend_with_attachments(file_data_group, new=True)

        return records

    # --------------------------------------------------------
    # Methods for grouping attachments
    # --------------------------------------------------------

    def _group_files_data_by_origin_attachment(self, files_data):
        """ A naive grouping method which does the following:

            - if a file_data has an 'origin_attachment', it is assigned to the same group as the 'origin_attachment'.
            - otherwise, it is assigned to a new group.
        """
        return [
            file_data_group
            for origin_attachment, file_data_group
            in groupby(files_data, lambda file_data: file_data['origin_attachment'])
        ]

    def _group_files_data_into_groups_of_mixed_types(self, files_data):
        """ A grouping method with a heuristic that enables it to dispatch files of the same type to
            different groups, but files of different types to the same group.

            This makes it suitable for grouping attachments received through a journal mail alias.
            For example, receiving 5 PDFs will dispatch them into 5 groups (one per PDF),
            but receiving one PDF, one JPG and one XML will dispatch them all into a single group.
        """
        files_data_with_origin_attachment = []
        files_data_without_origin_attachment = []
        for file_data in files_data:
            if 'decoder_info' not in file_data:
                file_data['decoder_info'] = self._get_edi_decoder(file_data, new=True)

            if file_data['origin_attachment'] == file_data['attachment']:
                files_data_without_origin_attachment.append(file_data)
            else:
                files_data_with_origin_attachment.append(file_data)

        groups = []
        # First dispatch the files_data that don't have an origin_attachment.
        sorted_files_data = sorted(
            files_data_without_origin_attachment,
            key=lambda file_data: (file_data['decoder_info'] or {}).get('priority', 0),
            reverse=True,
        )
        for file_data in sorted_files_data:
            self._assign_attachment_to_group_of_different_type(file_data, groups)

        # Then dispatch the files_data that have an origin_attachment.
        for file_data in files_data_with_origin_attachment:
            self._assign_attachment_to_group_with_same_origin_attachment(file_data, groups)

        return groups

    def _assign_attachment_to_group_of_different_type(self, incoming_file_data, groups=[]):
        """ Add the attachment to the group which doesn't yet have an attachment of the same root type
        (however, attachments with no root type don't clash with each other).
        If several groups are available, we choose the group which has the highest filename similarity.
        """
        incoming_type = incoming_file_data['import_file_type']

        # If there are groups with different types, we choose the group which has the highest filename similarity.
        if groups_with_different_type := [
            group
            for group in groups
            if not incoming_type or incoming_type not in (file_data['import_file_type'] for file_data in group)
        ]:
            sorted_by_similarity = sorted(
                groups_with_different_type,
                key=lambda group: max(
                    self._get_similarity_score(incoming_file_data['name'], file_data['name'])
                    for file_data in group
                ),
                reverse=True,
            )
            sorted_by_similarity[0].append(incoming_file_data)
            return

        # Otherwise, create a new group.
        groups.append([incoming_file_data])

    def _assign_attachment_to_group_with_same_origin_attachment(self, incoming_file_data, groups=[]):
        """ Attachments that come from the same origin attachment are added to the same group. """
        for group in groups:
            if any(
                incoming_file_data['origin_attachment'] == file_data['origin_attachment']
                for file_data in group
            ):
                group.append(incoming_file_data)
                return
        groups.append([incoming_file_data])

    def _get_similarity_score(self, filename1, filename2):
        """ Compute a similarity score between two filenames.
            This is used to group files with similar names together as much as possible
            when figuring out how to dispatch attachments received in a mail alias.

            Similarity is defined as the length of the largest common substring between
            the two filenames.
        """
        matcher = difflib.SequenceMatcher(a=filename1, b=filename2, autojunk=False)
        return matcher.find_longest_match().size

    # --------------------------------------------------------
    # Decoder framework
    # --------------------------------------------------------

    def _extend_with_attachments(self, files_data, new=False):
        """ Extend/enhance a business document with one or more attachments.

        Only the attachment with the highest priority will be used to extend the business document,
        using the appropriate decoder.

        The decoder may break Python and SQL constraints in difficult-to-predict ways.
        This method calls the decoder in such a way that any exceptions instead roll back the transaction
        and log a message on the invoice chatter.

        This method will not extract embedded files for you - if you want embedded files to be
        considered, you must pass them as part of the `attachments` recordset.

        :param self:        An invoice on which to apply the attachments.
        :param files_data:  A list of file_data dicts, each representing an in-DB or extracted attachment.
        :param new:         If true, indicates that the invoice was newly created, will be passed to the decoder.
        :return:            True if at least one document is successfully imported.

        ⚠️ Because this method commits the cursor, try to:
        (1) do as much work as possible before calling this method, and
        (2) avoid triggering a SerializationError later in the request. If a SerializationError happens,
            `retrying` will cause the whole request to be retried, which may cause some things
            to be duplicated. That may be more or less undesirable, depending on what you're doing.
        """
        def _get_attachment_name(file_data):
            params = {
                'filename': file_data['name'],
                'root_filename': file_data['origin_attachment'].name,
                'type': file_data['import_file_type'],
            }
            if not file_data['attachment']:
                return self.env._("'%(filename)s' (extracted from '%(root_filename)s', type=%(type)s)", **params)
            else:
                return self.env._("'%(filename)s' (type=%(type)s)", **params)

        self.ensure_one()

        for file_data in files_data:
            if 'decoder_info' not in file_data:
                file_data['decoder_info'] = self._get_edi_decoder(file_data, new=new)

        # Identify the attachment to decode.
        sorted_files_data = sorted(
            files_data,
            key=lambda file_data: (
                file_data['decoder_info'] is not None,
                (file_data['decoder_info'] or {}).get('priority', 0),
            ),
            reverse=True,
        )

        file_data = sorted_files_data[0]

        if file_data['decoder_info'] is None or file_data['decoder_info'].get('priority', 0) == 0:
            _logger.info(
                "Attachment(s) %s not imported: no suitable decoder found.",
                [file_data['name'] for file_data in files_data],
            )
            return

        try:
            with rollbackable_transaction(self.env.cr):
                reason_cannot_decode = file_data['decoder_info']['decoder'](self, file_data, new)
                if reason_cannot_decode:
                    self.message_post(
                        body=self.env._(
                            "Attachment %(filename)s not imported: %(reason)s",
                            filename=file_data['name'],
                            reason=reason_cannot_decode,
                        )
                    )
                    return
        except RedirectWarning:
            raise
        except Exception as e:
            _logger.exception("Error importing attachment %s on record %s", file_data['name'], self)

            self.sudo().message_post(body=Markup("%s<br/><br/>%s<br/>%s") % (
                self.env._(
                    "Error importing attachment %(filename)s:",
                    filename=_get_attachment_name(file_data),
                ),
                self.env._("This specific error occurred during the import:"),
                str(e),
            ))
            return
        return True

    def _get_edi_decoder(self, file_data, new=False):
        """ Main method that should be overridden to implement decoders for various file types.

        :param file_data: A dict representing an attachment which should be decoded.
        :param new:       (optional) whether the business document was newly created.
        :return:          A dict with the following keys:
            - decoder:     The decoder function to use. This function should return either None
                           if decoding was successful, or a string explaining why decoding failed.
            - priority:    The priority of the decoder.
        """
        pass

    # --------------------------------------------------------------
    # Helpers to consistently attach/unattach attachments to records
    # --------------------------------------------------------------

    def _attachment_fields_to_clear(self):
        """ Return a list of fields that should be cleared when an attachment is unattached from the record. """
        return []

    def _fix_attachments_on_record(self, attachments):
        """ Ensure that only attachments of certain types appear in `self`'s attachments.

        This is to provide a consistent behaviour where only certain attachment types
        appear in the chatter's attachments, to avoid cluttering the attachments view.
        """
        self.ensure_one()
        attachments_to_attach = attachments.filtered(self._should_attach_to_record)
        if attachments_to_attach:
            # No need to write to attachments that have the same res_model and res_id
            attachments_to_write = attachments_to_attach.filtered(lambda a: a.res_model != self._name or a.res_id != self.id)
            attachments_to_write.write({
                'res_model': self._name,
                'res_id': self.id,
            })
        attachments_to_unattach = (attachments - attachments_to_attach).filtered(lambda a: a.res_model == self._name and not a.res_field)
        if attachments_to_unattach:
            for fname in self._attachment_fields_to_clear():
                self[fname] -= attachments_to_unattach
            attachments_to_unattach.write({
                'res_model': False,
                'res_id': 0,
            })

    def _should_attach_to_record(self, attachment):
        """ Indicate whether a given attachment should be displayed in the record's attachments. """
        return attachment and not attachment.res_field and attachment.mimetype in {
            'text/csv',
            'application/pdf',
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/vnd.oasis.opendocument.spreadsheet',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.ms-powerpoint',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'application/vnd.oasis.opendocument.presentation',
        }

    # -------------------------------------------------------------------------
    # Helpers to convert between ir.attachment and file_data dicts
    # -------------------------------------------------------------------------

    @api.model
    def _to_files_data(self, attachments):
        """ Helper method to convert an ir.attachment recordset into an intermediate `files_data` format
            used by the import framework.

            :return: a list of dicts, each dict representing one of the attachments in `self`.
        """
        files_data = []
        for attachment in attachments:
            file_data = {
                'name': attachment.name,
                'raw': attachment.raw,
                'mimetype': attachment.mimetype,
                'origin_attachment': attachment,
                'attachment': attachment,
            }
            file_data['xml_tree'] = self._get_xml_tree(file_data)
            file_data['import_file_type'] = self._get_import_file_type(file_data)
            file_data['origin_import_file_type'] = file_data['import_file_type']
            files_data.append(file_data)
        return files_data

    @api.model
    def _from_files_data(self, files_data):
        """ Helper method to convert a `files_data` list-of-dicts back into an ir.attachment recordset.
            This only returns those elements in `files_data` which correspond to an ir.attachment
            (thus, embedded files that were never turned into ir.attachments are omitted).
        """
        return self.env['ir.attachment'].union(*(
            file_data['attachment']
            for file_data in files_data
            if file_data.get('attachment')
        ))

    @api.model
    def _get_import_file_type(self, file_data):
        """ Method to be overridden to identify a file's format. """
        if 'pdf' in file_data['mimetype'] or file_data['name'].endswith('.pdf'):
            return 'pdf'

    @api.model
    def _get_xml_tree(self, file_data):
        """ Parse file_data['raw'] into an lxml.etree.ElementTree.
            Can be overridden if custom decoding is needed.
        """
        if (
            # XML attachments received by mail have a 'text/plain' mimetype.
            'text/plain' in file_data['mimetype'] and (guess_mimetype(file_data['raw'] or b'').endswith('/xml') or file_data['name'].endswith('.xml'))
            or file_data['mimetype'].endswith('/xml')
        ):
            try:
                return etree.fromstring(file_data['raw'], parser=etree.XMLParser(remove_comments=True, resolve_entities=False))
            except etree.ParseError as e:
                _logger.info('Error when reading the xml file "%s": %s', file_data['name'], e)

    @api.model
    def _unwrap_attachments(self, files_data, recurse=True):
        """ Unwrap and return any embedded files.

        :param files_data: The files to be unwrapped.
        :param recurse: if True, embedded-of-embedded attachments will also be unwrapped and returned.
        :return: a `files_data` list representation of the embedded attachments.
        """
        return list(itertools.chain(*(self._unwrap_attachment(file_data, recurse=recurse) for file_data in files_data)))

    @api.model
    def _unwrap_attachment(self, file_data, recurse=True):
        """ Unwrap a single attachment and return its embedded attachments.

        This method can be overridden to implement custom unwrapping behaviours
        (e.g. EDI formats which contain multiple business documents in a single file)

        :param file_data: The file to be unwrapped.
        :param recurse: if True, should return embedded-of-embedded attachments.
        :return: a `files_data` list representation of the embedded attachements.
        """
        embedded = []
        if file_data['import_file_type'] == 'pdf':
            for filename, content in extract_pdf_embedded_files(file_data['name'], file_data['raw']):
                embedded_file_data = {
                    'name': filename,
                    'raw': content,
                    'mimetype': guess_mimetype(content),
                    'attachment': None,
                    'origin_attachment': file_data['origin_attachment'],
                    'origin_import_file_type': file_data['origin_import_file_type'],
                }
                embedded_file_data['xml_tree'] = self._get_xml_tree(embedded_file_data)
                embedded_file_data['import_file_type'] = self._get_import_file_type(embedded_file_data)
                embedded.append(embedded_file_data)

        if embedded and recurse:
            embedded.extend(self._unwrap_attachments(embedded))

        return embedded

    @api.model
    def _split_xml_into_new_attachments(self, file_data, tag):
        """ Helper method to split an XML file into multiple files on a given tag.

        In EDIs, some XMLs contain multiple business documents.
        In such cases, we often want any business document beyond the first to have its
        own attachment that can be decoded separately.
        This helper method looks whether the provided XML tree (given in `file_data`) has multiple
        instances of the given `tag`, and creates a new attachment for each tag beyond the first.
        The new attachment has the same XML structure as the original file, but only has one instance
        of the specified tag.

        :param file_data: The XML file to split
        :param tag: The tag which the XML file should be split on if there are multiple instances of it
        :return: a `files_data` list of files, for each business document beyond the first.
    """
        new_files_data = []
        if len(file_data['xml_tree'].findall(f'.//{tag}')) > 1:
            # Create a new xml tree for each invoice beyond the first
            trees = split_etree_on_tag(file_data['xml_tree'], tag)
            filename_without_extension, _dummy, extension = file_data['name'].rpartition('.')
            attachment_vals = [
                {
                    'name': f'{filename_without_extension}_{filename_index}.{extension}',
                    'raw': etree.tostring(tree),
                }
                for filename_index, tree in enumerate(trees[1:], start=2)
            ]
            created_attachments = self.env['ir.attachment'].create(attachment_vals)

            new_files_data.extend(self._to_files_data(created_attachments))
        return new_files_data
