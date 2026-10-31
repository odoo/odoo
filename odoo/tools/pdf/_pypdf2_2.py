from PyPDF2 import errors, filters, generic, PdfReader, PdfWriter as _Writer
from PyPDF2.generic import create_string_object
from PyPDF2._page import PageObject
from PyPDF2 import __version__  # noqa: F401

__all__ = [
    "PageObject",
    "PdfReader",
    "PdfWriter",
    "create_string_object",
    "errors",
    "filters",
    "generic",
]


class PdfWriter(_Writer):
    def getFields(self, *args, **kwargs):
        return self.get_fields(*args, **kwargs)

    def _addObject(self, *args, **kwargs):
        return self._add_object(*args, **kwargs)

    if hasattr(_Writer, '_resolve_indirect_object'):
        def _sweep_indirect_references(self, root):
            """
            Make every reference reachable from ``root`` point to an object of this writer.

            PyPDF2 >= 2.11 identifies objects by a hash of their content, and
            hashes all the parent objects again after each reference it
            rewrites - writing takes quadratic time on pages holding many
            references (annotations, resources).

            Objects of other documents are identified here by their Python identity instead.
            """
            translated = {
                id(obj): generic.IndirectObject(idnum, 0, self)
                for idnum, obj in enumerate(self._objects, 1)
            }

            def translate(reference):
                if reference.pdf is self:
                    return reference
                obj = reference.pdf.get_object(reference)
                if obj is None:
                    obj = generic.NullObject()
                if id(obj) not in translated:
                    translated[id(obj)] = self._add_object(obj)
                return translated[id(obj)]

            scanned = set()
            references = [translate(root)]
            while references:
                reference = references.pop()
                if reference.idnum in scanned:
                    continue
                scanned.add(reference.idnum)
                containers = [self._objects[reference.idnum - 1]]
                while containers:
                    container = containers.pop()
                    if isinstance(container, generic.DictionaryObject):
                        items = list(container.items())
                    elif isinstance(container, generic.ArrayObject):
                        items = list(enumerate(container))
                    else:
                        continue
                    for key, value in items:
                        if isinstance(value, generic.IndirectObject):
                            new_reference = translate(value)
                            if new_reference is not value:
                                container[key] = new_reference
                            references.append(new_reference)
                        elif isinstance(value, generic.StreamObject):
                            # streams must be indirect objects
                            new_reference = self._add_object(value)
                            translated[id(value)] = new_reference
                            container[key] = new_reference
                            references.append(new_reference)
                        elif isinstance(value, (generic.DictionaryObject, generic.ArrayObject)):
                            containers.append(value)
