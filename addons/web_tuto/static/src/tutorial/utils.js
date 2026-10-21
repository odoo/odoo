import { queryAllTexts, queryFirst, queryRect } from "@odoo/hoot-dom";
import { _t } from "@web/core/l10n/translation";
import { closestScrollableY } from "@web/core/utils/scrolling";

/**
 * @returns {ParentNode} the dialog on top of the others if any, the document
 *   otherwise
 */
export function getRoot() {
    return queryFirst(".modal", { visible: true, last: true }) || document;
}

/**
 * @param {ParentNode} root
 * @returns {{ anchor: HTMLElement, content: string } | undefined} the first
 *   invalid field displayed in the root, with the help asking to fill it in
 */
export function findInvalidField(root) {
    const field = queryFirst(".o_field_widget.o_field_invalid, .o_invalid_cell", {
        root,
        visible: true,
    });
    if (!field) {
        return;
    }
    const anchor =
        queryFirst("input, textarea, [contenteditable=true]", { root: field, visible: true }) ||
        field;
    const [label] = anchor.id
        ? queryAllTexts(`label[for="${CSS.escape(anchor.id)}"]`, { root })
        : [];
    return {
        anchor,
        content: label
            ? _t("Fill in “%(field)s” to go on with the tutorial.", { field: label })
            : _t("Fill in this field to go on with the tutorial."),
    };
}

/**
 * @param {Element} element
 * @returns {boolean} whether another element (e.g. an open dropdown) is on top
 *   of the visible center of the element, the pointer itself excepted
 */
export function isCovered(element) {
    const { left, top, width, height } = queryRect(element);
    const [x, y] = [left + width / 2, top + height / 2];
    const visible = queryRect(closestScrollableY(element) || element.ownerDocument.body);
    if (
        !width ||
        !height ||
        x < Math.max(visible.left, 0) ||
        x > Math.min(visible.right, window.innerWidth) ||
        y < Math.max(visible.top, 0) ||
        y > Math.min(visible.bottom, window.innerHeight)
    ) {
        return false;
    }
    const topElement = element.ownerDocument.elementFromPoint(x, y);
    return Boolean(
        topElement &&
            !element.contains(topElement) &&
            !topElement.contains(element) &&
            !topElement.closest(".o_tutorial_pointer")
    );
}

/**
 * The views showing several records (all but the form) show the same records,
 * a chapter of one of them being shown in any of them
 * @param {string} type the type of the view of a chapter
 * @param {string} displayedType the type of the displayed view
 * @returns {boolean}
 */
export function isSameViewType(type, displayedType) {
    return type === displayedType || (type !== "form" && displayedType !== "form");
}
