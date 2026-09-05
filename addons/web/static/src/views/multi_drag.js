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
 * Records being edited are left out: saving them as a side effect of the drag
 * would silently commit their pending changes.
 *
 * @param {import("@web/model/relational_model/dynamic_list").DynamicList} list
 * @param {string} draggedId
 * @returns {string[] | null}
 */
export function getMultiDragRecordIds(list, draggedId) {
    const ids = list.selection.filter((record) => !record.isInEdition).map((record) => record.id);
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
 * @param {string} params.placeholderTag
 * @param {string} params.placeholderClass
 * @param {string} [params.keptChildSelector] child of the dragged element to keep visible
 */
export function startMultiDrag(
    root,
    element,
    recordIds,
    { placeholderTag, placeholderClass, keptChildSelector }
) {
    for (const child of element.children) {
        if (!keptChildSelector || !child.matches(keptChildSelector)) {
            hide(child);
        }
    }
    for (const id of recordIds) {
        if (id !== element.dataset.id) {
            hide(root.querySelector(`[data-id="${CSS.escape(id)}"]`));
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
