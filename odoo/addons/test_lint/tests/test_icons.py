# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from lxml import etree

from .common import LintCase

# matches the `fa` and `fa-*` classes of the FontAwesome icon set
FA_CLASS_RE = re.compile(r'(?<![\w-])fa(?:-[\w-]+)*(?![\w-])')

# `oi` alone flags an element as an Odoo icon, and a limited set of `oi-*`
# classes are still supported to tweak how it is rendered (sizing, animations,
# stacking, ...). Any other `oi-*` class is an obsolete icon-name class, which
# must be replaced by the `data-icon` attribute.
OI_MODIFIERS = ('filled', 'fw', 'stack', 'pulse', 'spin', 'rotate', 'flip', 'sm', 'lg', r'\d{1,2}x')
OBSOLETE_OI_CLASS_RE = re.compile(r'(?<![\w-])oi-(?!%s)[\w-]+' % '|'.join(OI_MODIFIERS))

# Files still setting icons through classes in their templates/views.
# Do NOT add new entries: icons must be set through the `data-icon` attribute
# (e.g. `<i class="oi" data-icon="person"/>`), and entries should be removed
# from this list as they get ported.
ICON_CLASSES_WHITELIST = {
    'spreadsheet/static/src/o_spreadsheet/o_spreadsheet.xml',
}


class TestIcons(LintCase):

    def iter_icon_values(self, path):
        """ Yields the values of every attribute able to set an icon on an
        element of the given xml file: the class-setting ones (``class``,
        ``t-att-class``, ``t-attf-class``, ...), the ``icon`` ones (``icon``,
        ``t-att-icon``, ...) and the classes set through
        ``<attribute name="class">`` view inheritance.
        """
        try:
            tree = etree.parse(path)
        except etree.XMLSyntaxError:
            return  # invalid xml files are the concern of other tests
        for element in tree.iter(etree.Element):
            for name, value in element.attrib.items():
                if name.endswith(('class', 'icon')):
                    yield value
            if element.tag == 'attribute' and (element.get('name') or '').endswith(('class', 'icon')):
                yield element.text or ''
                yield element.get('add') or ''
                yield element.get('remove') or ''

    def test_no_legacy_icon_classes(self):
        """ Test that no icon is set through a class in xml files """
        for path in self.iter_module_files('*.xml'):
            if any(path.endswith(f'/{whitelisted}') for whitelisted in ICON_CLASSES_WHITELIST):
                continue
            with self.subTest(file=path):
                found_old_oi_icons = set()
                found_fontawesome_icons = set()
                for value in self.iter_icon_values(path):
                    found_fontawesome_icons.update(FA_CLASS_RE.findall(value))
                    found_old_oi_icons.update(OBSOLETE_OI_CLASS_RE.findall(value))
                self.assertFalse(
                    found_fontawesome_icons,
                    f"Obsolete FontAwesome icon class(es) {', '.join(sorted(found_fontawesome_icons))} found in {path}.\n"
                    "Please use Material Symbols icons using the "
                    "`data-icon` attribute instead, e.g. `<i class=\"oi\" data-icon=\"person\"/>`.\n"
                    "See https://www.odoo.com/documentation/master/developer/reference/user_interface/icons.html#migration-from-font-awesome for more information on how to migrate.",
                )
                self.assertFalse(
                    found_old_oi_icons,
                    f"Obsolete Odoo icon class(es) {', '.join(sorted(found_old_oi_icons))} found in {path}.\n"
                    "Please use the new Odoo icons set using the "
                    "`data-icon` attribute instead, e.g. `<i class=\"oi\" data-icon=\"oi_view-kanban\"/>`.\n"
                    "See https://www.odoo.com/documentation/master/developer/reference/user_interface/icons.html#odoo-ui-icons for more information.",
                )
