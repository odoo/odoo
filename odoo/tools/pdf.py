# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import io
import pikepdf

from pikepdf import Pdf

from odoo.tools.parse_version import parse_version as pv
if pv(pikepdf.__version__) >= pv('3.0.0'):
    from pikepdf import AttachedFileSpec
else:
    from pikepdf import Array, Dictionary, Name, Stream

class OdooPdf(Pdf):
    def _save(self, *args, **kwargs):
        with self.open_metadata(set_pikepdf_as_editor=False) as meta:
            meta['xmp:CreatorTool'] = 'Odoo'
            meta['pdf:Producer'] = "Odoo"
        self.save_bak(*args, **kwargs)

    if pv(pikepdf.__version__) >= pv('3.0.0'):
        def _get_attachments(self):
            for key, value in self.attachments.items():
                yield key, value.get_file().read_bytes()

        def _add_attachment(self, fname, fdata):
            self.attachments[fname] = AttachedFileSpec(self, data=fdata)

    else:
        def _get_attachments(self):
            if '/Names' not in self.Root or '/EmbeddedFiles' not in self.Root.Names or '/Names' not in self.Root.Names.EmbeddedFiles:
                return []
            attachments = list(self.Root.Names.EmbeddedFiles.Names)
            for i in range(0, len(attachments), 2):
                yield attachments[i], attachments[i + 1]["/EF"]["/F"].read_bytes()

        def _add_attachment(self, fname, fdata):
            self._set_attachment(basename=fname, filebytes=fdata)

        def _set_attachment(self, *, basename, filebytes, mime=None, desc=''):
            """
            Attach a file to this PDF

            Args:
                basename (str): The basename (filename withouth path) to name the
                    file. Not necessarily the name of the file on disk. Will be s
                    hown to the user by the PDF viewer. filebytes (bytes): The file
                    contents.

                mime (str or None): A MIME type for the filebytes. If omitted, we try
                    to guess based on the standard library's
                    :func:`mimetypes.guess_type`. If this cannot be determined, the
                    generic value `application/octet-stream` is used. This value is
                    used by PDF viewers to decide how to present the information to
                    the user.

                desc (str): A extended description of the file contents. PDF viewers
                    also display this information to the user. In Acrobat DC this is
                    hidden in a context menu.

            This function is mainly copied of the original _attach function of pikepdf
            (<3.0.0). Comparing with the original _attach, the existing attachments of
            the PDF will not be removed. Also, in order to have similar behavior of
            pikepdf(>= 3.0.0), existing attachments with the same basename will be
            replaced with the new attachment.
            Notes:Pdf which has attachments with the same name will have nondeterministic
            behavior

            """
            if '/Names' not in self.Root:
                self.Root.Names = self.make_indirect(Dictionary())
            if '/EmbeddedFiles' not in self.Root.Names:
                self.Root.Names.EmbeddedFiles = self.make_indirect(Dictionary())
            if '/Names' not in self.Root.Names.EmbeddedFiles:
                self.Root.Names.EmbeddedFiles.Names = Array()

            if '/' in basename or '\\' in basename:
                raise ValueError("basename should be a basename (no / or \\)")

            if not mime:
                from mimetypes import guess_type

                mime, _encoding = guess_type(basename)
                if not mime:
                    mime = 'application/octet-stream'

            filestream = Stream(self, filebytes)
            filestream.Subtype = Name('/' + mime)

            filespec = Dictionary(
                {
                    '/Type': Name.Filespec,
                    '/F': basename,
                    '/UF': basename,
                    '/Desc': desc,
                    '/EF': Dictionary({'/F': filestream}),
                }
            )

            attachments = list(self.Root.Names.EmbeddedFiles.Names)
            try:
                index = attachments.index(basename)
                del attachments[index]
                del attachments[index]
            except Exception:
                pass
            self.Root.Names.EmbeddedFiles.Names = Array(attachments + [basename, self.make_indirect(filespec)])

            if '/PageMode' not in self.Root:
                self.Root.PageMode = Name.UseAttachments

        Pdf._set_attachment = _set_attachment

    Pdf.add_attachment = _add_attachment
    Pdf.get_attachments = _get_attachments
    Pdf.save_bak = Pdf.save
    Pdf.save = _save


def merge_pdf(pdfs_data):
    ''' Merge a collection of PDF documents in one.
    Note that the attachments are not merged.
    :param list pdf_data: a list of PDF datastrings
    :return: a unique merged PDF datastring
    '''
    merged = OdooPdf.new()
    for pdf_data in pdfs_data:
        with OdooPdf.open(io.BytesIO(pdf_data)) as src:
            merged.pages.extend(src.pages)
    with io.BytesIO() as _buffer:
        merged.save(_buffer)
        return _buffer.getvalue()


def rotate_pdf(pdf_data):
    ''' Rotate clockwise PDF (90°) into a new PDF.
    :param pdf: a PDF to rotate
    :return: a PDF rotated
    '''
    with OdooPdf.open(io.BytesIO(pdf_data)) as pdf, io.BytesIO() as _buffer:
        for page in pdf.pages:
            page.rotate(90, relative=True)
        pdf.save(_buffer)
        return _buffer.getvalue()
