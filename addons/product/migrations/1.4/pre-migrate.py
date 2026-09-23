r"""Pre-migration: follow the documents-button *locator* moving to a span.

``documents_product`` used to put the Documents stat button straight into
``product.view_product_template_form``, so four modules located it by name to
place their own buttons beside it::

    <button name="action_view_documents" position="before">

That module now lives in core and inherits ``view_product_template_form_only``
instead, adding the button *below* the views that used to locate it. What they
anchor on now is the empty marker the common form carries for the purpose,
``<span id="button_documents_before"/>`` -- ``stock/views/product_views.xml``
and ``mrp/views/product_views.xml`` already use it, and ``sale`` and
``purchase`` no longer reference the button at all.

Without this the upgrade dies before those files are read. ``product`` reloads
``view_product_template_form`` first, and writing a view revalidates everything
inheriting it -- so the six stored arches still holding the old locator are
combined against a parent that no longer has that button, raising "Element
<button name='action_view_documents'> cannot be located in parent view". Each
of those views is rewritten from its own module's data file later in the same
upgrade; they only have to survive that window.

Only elements carrying a ``position`` attribute are rewritten. That is what
distinguishes a *locator* from the button's real definition, which the parent
form still holds in its stored arch until the data file replaces it, and which
must not be turned into a span.
"""

import json
import logging
import typing

from lxml import etree

if typing.TYPE_CHECKING:
    from odoo.db.cursor import Cursor

_logger = logging.getLogger(__name__)

OLD_NAME = "action_view_documents"
NEW_TAG = "span"
NEW_ID = "button_documents_before"
MODELS = ("product.template", "product.product")


def migrate(cr: Cursor, version: str | None) -> None:
    if not version:
        return

    cr.execute(
        """
        SELECT id, arch_db FROM ir_ui_view
         WHERE model = ANY(%s) AND arch_db::text LIKE %s
        """,
        (list(MODELS), f"%{OLD_NAME}%"),
    )
    rows = cr.fetchall()

    patched = 0
    for view_id, arch in rows:
        translations = arch if isinstance(arch, dict) else json.loads(arch)
        new_translations = {}
        changed = False
        for lang, source in translations.items():
            rewritten, hits = _rewrite(source)
            new_translations[lang] = rewritten
            changed = changed or bool(hits)
        if not changed:
            continue
        cr.execute(
            "UPDATE ir_ui_view SET arch_db = %s WHERE id = %s",
            (json.dumps(new_translations), view_id),
        )
        patched += 1

    if patched:
        _logger.info(
            "Repointed the documents-button locator at <%s id=%r> in %d stored "
            "view arch(s)",
            NEW_TAG,
            NEW_ID,
            patched,
        )


def _rewrite(source: str) -> tuple[str, int]:
    """Turn every ``<button name=OLD_NAME position=...>`` locator into a span."""
    try:
        root = etree.fromstring(f"<wrap>{source}</wrap>")
    except etree.XMLSyntaxError:
        return source, 0

    hits = 0
    for node in root.xpath(f"//button[@name='{OLD_NAME}'][@position]"):
        node.tag = NEW_TAG
        del node.attrib["name"]
        node.set("id", NEW_ID)
        hits += 1
    if not hits:
        return source, 0

    inner = (root.text or "") + "".join(
        etree.tostring(child, encoding="unicode") for child in root
    )
    return inner, hits
