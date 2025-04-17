import { useNavigation } from "../navigation/navigation";

/**
 * This hook allows to navigate between tags in a record selector. It also
 * allows to delete tags with the backspace key.
 * It is meant to be used in component which contains both the components
 * `Autocomplete` and `TagList`.
 *
 * @param {string} refName Name of the t-ref which contains the `Autocomplete` and `TagList` components.
 * @param {object} [options]
 * @param {() => boolean} [options.isEnabled]
 * @param {(index: number) => void} [options.delete] Function to be called when a tag is deleted. It should take the index of the tag to delete as parameter.
 */
export function useTagNavigation(refName, options = {}) {
    const isEnabled = options.isEnabled ?? (() => true);

    const isNavigationAvailable = (navigator, target) => {
        return isEnabled() && navigator.items.some((item) => item.target === target);
    };

    const canRemoveTag = (target) => {
        return options.delete && (target.tagName.toLowerCase() !== "input" || !target.value);
    };

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
            const menu = navigator.containerRef.el.querySelector(".o-autocomplete--dropdown-menu");
            const index = navNext ? el.value.length : 0;
            if (el.selectionStart !== index || menu) {
                return false;
            }
        }
        return true;
    };

    useNavigation(refName, {
        itemsSelector: ":scope .o_tag, :scope .o-autocomplete--input",
        onEnabled() {}, // prevent auto focus
        focusInitialElementOnDisabled: () => false,
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
                isAvailable: (navigator, target) => isNavigationAvailable(navigator, target) && canRemoveTag(target),
                callback: (navigator) => onBackspaceKeydown(navigator),
            },
            arrowleft: {
                bypassEditableProtection: true,
                isAvailable: (navigator, target) => isNavigationAvailable(navigator, target) && canNavigateFromInput(navigator, false),
                callback: (navigator) => navigator.previous(),
            },
            arrowright: {
                bypassEditableProtection: true,
                isAvailable: (navigator, target) => isNavigationAvailable(navigator, target) && canNavigateFromInput(navigator, true),
                callback: (navigator) => navigator.next(),
            },
        },
    });
}
