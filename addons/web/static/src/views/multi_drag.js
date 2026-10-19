import { _t } from "@web/core/l10n/translation";

// Hidden and not removed from the DOM, as those elements back live Owl components.
const HIDDEN_CLASSES = ["o_multi_drag_hidden", "d-none"];

/**
 * `o_multi_drag_hidden` marks the elements `d-none` was added on, so that
 * `stopMultiDrag` never reveals an element that was already hidden on its own:
 * Owl wouldn't put back a `d-none` written straight in a template.
 *
 * @param {HTMLElement} [el]
 */
function hide(el) {
    if (el && !el.classList.contains("d-none")) {
        el.classList.add(...HIDDEN_CLASSES);
    }
}

/**
 * Ids of the records to drag together, or null for a plain single record drag.
 *
 * @param {import("@web/model/relational_model/dynamic_list").DynamicList} list
 * @param {string} draggedId
 * @param {Object} [options]
 * @param {boolean} [options.sameGroupOnly] leave behind the selected records of the
 *  other groups, for a view where a record may not change group
 * @returns {string[] | null}
 */
export function getMultiDragRecordIds(list, draggedId, { sameGroupOnly } = {}) {
    let selection = list.selection;
    if (sameGroupOnly) {
        const { group } = selection.find((record) => record.id === draggedId) || {};
        selection = selection.filter((record) => record.group === group);
    }
    const ids = selection.map((record) => record.id);
    return ids.length > 1 && ids.includes(draggedId) ? ids : null;
}

/**
 * Consolidates a multi record drag into a single block: the other dragged records
 * and the content of the dragged element are hidden, and a placeholder telling how
 * many records are being moved takes their place. Undone by `stopMultiDrag`.
 *
 * @param {HTMLElement} root
 * @param {HTMLElement} element the dragged element
 * @param {string[]} recordIds ids of the records dragged together
 * @param {Object} params
 * @param {string} params.recordSelector matches a record element, and only those: groups
 *  carry a `data-id` of their own
 * @param {string} params.placeholderTag
 * @param {string} params.placeholderClass
 * @param {string} [params.leadingChildSelector] leading children left visible, so that
 *  the placeholder starts where the record's content does
 */
export function startMultiDrag(
    root,
    element,
    recordIds,
    { recordSelector, placeholderTag, placeholderClass, leadingChildSelector }
) {
    let isLeading = Boolean(leadingChildSelector);
    for (const child of element.children) {
        isLeading = isLeading && child.matches(leadingChildSelector);
        if (!isLeading) {
            hide(child);
        }
    }
    for (const id of recordIds) {
        if (id !== element.dataset.id) {
            hide(root.querySelector(`${recordSelector}[data-id="${CSS.escape(id)}"]`));
        }
    }
    const placeholder = document.createElement(placeholderTag);
    placeholder.className = `o_multi_drag_placeholder ${placeholderClass}`;
    placeholder.textContent = _t("Move %(count)s records", { count: recordIds.length });
    element.appendChild(placeholder);
}

/**
 * @param {HTMLElement | null} root
 */
export function stopMultiDrag(root) {
    for (const el of root?.querySelectorAll(".o_multi_drag_hidden") || []) {
        el.classList.remove(...HIDDEN_CLASSES);
    }
    root?.querySelector(".o_multi_drag_placeholder")?.remove();
}
