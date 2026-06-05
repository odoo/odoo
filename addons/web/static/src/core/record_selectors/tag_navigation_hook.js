import { useRef } from "@web/owl2/utils";
import { useNavigation } from "../navigation/navigation";

/**
 * Resolves the element backing a `ref` regardless of its kind, preserving the
 * legacy forms and ADDING the Owl 3 native signal case. Null-safe: never throws.
 * - undefined/null ref           -> undefined (mirrors the old `ref.el`)
 * - object refs (useRef)         -> `.el`
 * - forwarded refs (useChildRef) -> callables exposing an `.el` getter; read
 *   `.el` (never call them, that would clear their value).
 * - Owl 3 native signal refs     -> zero-argument callables with no `.el`,
 *   resolved by calling them.
 * @param {{ el?: HTMLElement } | (() => HTMLElement) | null | undefined} ref
 * @returns {HTMLElement | null | undefined}
 */
function resolveRefEl(ref) {
    if (ref == null) {
        return undefined;
    }
    if (typeof ref !== "function") {
        return ref.el;
    }
    if (ref.length > 0 || "el" in ref) {
        return ref.el;
    }
    return ref();
}

/**
 * This hook allows to navigate between tags in a record selector. It also
 * allows to delete tags with the backspace key.
 * It is meant to be used in component which contains both the components
 * `Autocomplete` and `TagList`.
 *
 * @param {string|object|(() => HTMLElement)} refName Name of the t-ref which contains
 *      the `Autocomplete` and `TagList` components, or a ref object / Owl 3 native
 *      signal ref pointing to that container.
 * @param {object} [options]
 * @param {() => boolean} [options.isEnabled]
 * @param {(index: number) => void} [options.delete] Function to be called when a tag is deleted. It should take the index of the tag to delete as parameter.
 */
export function useTagNavigation(refName, options = {}) {
    // Backward-compatible: a string is resolved through the (compat) `useRef`,
    // exactly as before. A ref object or an Owl 3 native signal ref is used
    // directly (both are accepted by `useNavigation`, which resolves them).
    const tagsContainerRef = typeof refName === "string" ? useRef(refName) : refName;

    const isEnabled = options.isEnabled ?? (() => true);

    const canRemoveTag = (target) =>
        options.delete && (target.tagName.toLowerCase() !== "input" || !target.value);

    const onBackspaceKeydown = (navigator) => {
        const el = navigator.activeItem.el;
        if (el.classList.contains("o-autocomplete--input")) {
            if (!el.value && navigator.items.length > 1) {
                options.delete(navigator.items.length - 2);
            }
        } else {
            options.delete(navigator.activeItemIndex);
        }
        navigator.items.at(-1).setActive();
    };

    const canNavigateFromInput = (navigator, navNext) => {
        const el = navigator.activeItem.el;
        if (el.classList.contains("o-autocomplete--input")) {
            if (el.value.length) {
                return false;
            }
        }
        return true;
    };

    useNavigation(tagsContainerRef, {
        getItems: () =>
            resolveRefEl(tagsContainerRef)?.querySelectorAll(
                ":scope .o_tag, :scope .o-autocomplete--input"
            ) ?? [],
        isNavigationAvailable: ({ navigator, target }) =>
            isEnabled() && navigator.isFocused && navigator.contains(target),
        hotkeys: {
            tab: null,
            "shift+tab": null,
            home: null,
            end: null,
            enter: null,
            arrowup: null,
            arrowdown: null,
            backspace: {
                bypassEditableProtection: true,
                isAvailable: ({ target }) => canRemoveTag(target),
                callback: (navigator) => onBackspaceKeydown(navigator),
            },
            arrowleft: {
                bypassEditableProtection: true,
                isAvailable: ({ navigator }) => canNavigateFromInput(navigator, false),
                callback: (navigator) => navigator.previous(),
            },
            arrowright: {
                bypassEditableProtection: true,
                isAvailable: ({ navigator }) => canNavigateFromInput(navigator, true),
                callback: (navigator) => navigator.next(),
            },
        },
    });
}
