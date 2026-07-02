import { onPatched } from "@odoo/owl";
import { localization } from "@web/core/l10n/localization";

/**
 * Reorders a list with the arrow keys, from a focused drag handle: up and down
 * move the item among its siblings, left and right (mirrored in RTL) nest and
 * un-nest it. The handle is focused back once the move is rendered.
 *
 * @param {Object} params
 * @param {(item: any) => any[]} params.getList siblings of `item`, in order
 * @param {(item: any, previous: any) => void} params.insertAfter moves `item`
 *      after `previous` (null = first position)
 * @param {(item: any) => HTMLElement|null} params.getHandle handle to focus
 *      back
 * @param {(item: any, direction: -1|1) => boolean} [params.onNest] nests (1) or
 *      un-nests (-1) `item`, and returns whether it moved
 * @returns {{restoreFocus: Function, onHandleKeyDown: Function}}
 */
export function useKeyboardReorder({ getList, insertAfter, getHandle, onNest }) {
    let itemToFocus = null;

    // Re-focuses the drag handle after the reorder rebuilds the DOM.
    const restoreFocus = () => {
        const handleEl = itemToFocus && getHandle(itemToFocus);
        if (handleEl) {
            itemToFocus = null;
            handleEl.focus();
        }
    };
    onPatched(restoreFocus);

    /**
     * @param {any} item
     * @param {-1|1} direction
     * @returns {boolean} whether the item moved
     */
    function move(item, direction) {
        const items = getList(item);
        const index = items.indexOf(item);
        const newIndex = index + direction;
        if (newIndex < 0 || newIndex >= items.length) {
            return false;
        }
        insertAfter(item, (direction < 0 ? items[newIndex - 1] : items[newIndex]) ?? null);
        return true;
    }

    return {
        restoreFocus,
        onHandleKeyDown(ev, item) {
            const isRTL = localization.direction === "rtl";
            const handler = {
                ArrowUp: () => move(item, -1),
                ArrowDown: () => move(item, 1),
                ...(onNest && {
                    ArrowLeft: () => onNest(item, isRTL ? 1 : -1),
                    ArrowRight: () => onNest(item, isRTL ? -1 : 1),
                }),
            }[ev.key];
            if (handler) {
                ev.preventDefault();
                ev.stopPropagation();
                if (handler()) {
                    itemToFocus = item;
                }
            }
        },
    };
}
