/** @odoo-module */

import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";

import { useEffect, useRef } from "@odoo/owl";

/**
 * This hook allows to navigate between tags in a record selector. It also
 * allows to delete tags with the backspace key.
 * It is meant to be used in component which contains both the components
 * `Autocomplete` and `TagList`.
 *
 * @param {string} refName Name of the t-ref which contains the `Autocomplete` and `TagList` components.
 * @param {Function} deleteTag Function to be called when a tag is deleted. It should take the index of the tag to delete as parameter.
 * @returns {Function} Function to be called when a tag is focused and a key is pressed. It should be passed to the `onKeydown` prop of the `Tag` component.
 */
export function useTagNavigation(refName, deleteTag) {
    const ref = useRef(refName);

    useEffect(
        (autocomplete) => {
            if (!autocomplete) {
                return;
            }
            autocomplete.addEventListener("keydown", onAutoCompleteKeydown);
            return () => {
                autocomplete.removeEventListener("keydown", onAutoCompleteKeydown);
            };
        },
        () => [ref.el?.querySelector(".o-autocomplete")]
    );

    /**
     * Focus the tag at the given index. If no index is given, focus the rightmost tag.
     * @param {number|undefined} index Index of the tag to focus. If undefined, focus the rightmost tag.
     */
    function focusTag(index) {
        const tags = ref.el.getElementsByClassName("o_tag");
        if (tags.length) {
            if (index === undefined) {
                tags[tags.length - 1].focus();
            } else {
                tags[index].focus();
            }
        }
    }

    /**
     * Function to be called when a key is pressed in the `Autocomplete` component.
     *
     * @param {Event} ev
     */
    function onAutoCompleteKeydown(ev) {
        if (ev.isComposing) {
            // This case happens with an IME for example: we let it handle all key events.
            return;
        }
        const hotkey = getActiveHotkey(ev);
        const input = ev.target.closest(".o-autocomplete--input");
        const autoCompleteMenuOpened = !!ref.el.querySelector(".o-autocomplete--dropdown-menu");
        switch (hotkey) {
            case "arrowleft": {
                if (input.selectionStart || autoCompleteMenuOpened) {
                    return;
                }
                // focus rightmost tag if any.
                focusTag();
                break;
            }
            case "arrowright": {
                if (input.selectionStart !== input.value.length || autoCompleteMenuOpened) {
                    return;
                }
                // focus leftmost tag if any.
                focusTag(0);
                break;
            }
            case "backspace": {
                if (input.value) {
                    return;
                }
                const tags = ref.el.getElementsByClassName("o_tag");
                if (tags.length) {
                    deleteTag(tags.length - 1);
                }
                break;
            }
            default:
                return;
        }
        ev.preventDefault();
        ev.stopPropagation();
    }

    /**
     * Function to be called when a key is pressed in the `Tag` component.
     * It should be passed to the `onKeydown` prop of the `Tag` component.
     *
     * @param {Event} ev
     */
    function onTagKeydown(ev) {
        const hotkey = getActiveHotkey(ev);
        const tags = [...ref.el.getElementsByClassName("o_tag")];
        const closestTag = ev.target.closest(".o_tag");
        const tagIndex = tags.indexOf(closestTag);
        const input = ref.el.querySelector(".o-autocomplete--input");
        switch (hotkey) {
            case "arrowleft": {
                if (tagIndex === 0) {
                    input.focus();
                } else {
                    focusTag(tagIndex - 1);
                }
                break;
            }
            case "arrowright": {
                if (tagIndex === tags.length - 1) {
                    input.focus();
                } else {
                    focusTag(tagIndex + 1);
                }
                break;
            }
            case "backspace": {
                input.focus();
                deleteTag(tagIndex);
                break;
            }
            default:
                return;
        }
        ev.preventDefault();
        ev.stopPropagation();
    }

    return onTagKeydown;
}
