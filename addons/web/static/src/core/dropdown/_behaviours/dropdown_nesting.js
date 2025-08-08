import { EventBus, onWillDestroy, useChildSubEnv, useEffect, useEnv } from "@odoo/owl";
import { localization } from "@web/core/l10n/localization";
import { useBus, useService } from "@web/core/utils/hooks";
import { effect } from "@web/core/utils/reactive";

export const DROPDOWN_NESTING = Symbol("dropdownNesting");
const BUS = new EventBus();

class DropdownNestingState {
    constructor({ parent, close }) {
        this._isOpen = false;
        this.parent = parent;
        this.children = new Set();
        this.close = close;

        parent?.children.add(this);
    }

    set isOpen(value) {
        this._isOpen = value;
        if (this._isOpen) {
            BUS.trigger("dropdown-opened", this);
        }
    }

    get isOpen() {
        return this._isOpen;
    }

    remove() {
        this.parent?.children.delete(this);
    }

    closeAllParents() {
        this.close();
        if (this.parent) {
            this.parent.closeAllParents();
        }
    }

    closeChildren() {
        this.children.forEach((child) => child.close());
    }

    shouldIgnoreChanges(other) {
        return (
            other === this ||
            other.activeEl !== this.activeEl ||
            [...this.children].some((child) => child.shouldIgnoreChanges(other))
        );
    }

    handleChange(other) {
        // Prevents closing the dropdown when a change is coming from itself or from a children.
        if (this.shouldIgnoreChanges(other)) {
            return;
        }

        if (other.isOpen && this.isOpen) {
            this.close();
        }
    }
}

/**
 * This hook is used to manage communication between dropdowns.
 *
 * When a dropdown is open, every other dropdown that is not a parent
 * is closed. It also uses the current's ui active element to only
 * close itself when the active element is the same as the current
 * dropdown to separate dropdowns in different dialogs.
 *
 * @param {import("@web/core/dropdown/dropdown_hooks").DropdownState} state
 * @returns
 */
export function useDropdownNesting(state) {
    const env = useEnv();
    const current = new DropdownNestingState({
        parent: env[DROPDOWN_NESTING],
        close: () => state.close(),
    });

    // Set up UI active element related behavior ---------------------------
    const uiService = useService("ui");
    useEffect(
        () => {
            Promise.resolve().then(() => {
                current.activeEl = uiService.activeElement;
            });
        },
        () => []
    );

    useChildSubEnv({ [DROPDOWN_NESTING]: current });
    useBus(BUS, "dropdown-opened", ({ detail: other }) => current.handleChange(other));

    effect(
        (state) => {
            current.isOpen = state.isOpen;
        },
        [state]
    );

    onWillDestroy(() => {
        current.remove();
    });

    const isDropdown = (target) => target && target.classList?.contains("o-dropdown");
    const isRTL = () => localization.direction === "rtl";

    return {
        get hasParent() {
            return Boolean(current.parent);
        },
        /**@type {import("@web/core/navigation/navigation").NavigationOptions} */
        navigationOptions: {
            onUpdated: (navigator) => {
                if (current.parent && !navigator.activeItem) {
                    navigator.items[0]?.setActive();
                }
            },
            hotkeys: {
                escape: () => current.close(),
                arrowleft: {
                    isAvailable: ({ target }) => current.parent || (isRTL() && isDropdown(target)),
                    callback: (navigator) => {
                        if (isRTL() && isDropdown(navigator.activeItem?.target)) {
                            navigator.activeItem?.select();
                        } else if (current.parent) {
                            current.close();
                        }
                    },
                },
                arrowright: {
                    isAvailable: ({ target }) => isDropdown(target) || (isRTL() && current.parent),
                    callback: (navigator) => {
                        if (isRTL() && current.parent) {
                            current.close();
                        } else if (isDropdown(navigator.activeItem?.target)) {
                            navigator.activeItem?.select();
                        }
                    },
                },
            },
        },
    };
}
