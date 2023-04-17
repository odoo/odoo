/** @odoo-module **/

import { useEffect, useEnv, EventBus, useChildSubEnv, onWillDestroy } from "@odoo/owl";
import { localization } from "@web/core/l10n/localization";
import { useBus } from "@web/core/utils/hooks";

export const ClosingMode = {
    None: "none",
    ClosestParent: "closest",
    AllParents: "all",
};

export const DROPDOWN = Symbol("DropdownNesting");
const BUS = new EventBus();

class DropdownNestingState {
    constructor({ parent, close, containerRef }) {
        this._isOpen = false;
        this.containerRef = containerRef;
        this.parent = parent;
        this.children = new Set();
        this.close = close;

        parent?.children.add(this);
    }

    set isOpen(value) {
        this._isOpen = value;
        BUS.trigger("state-changed", this);
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
            other === this || [...this.children].some((child) => child.shouldIgnoreChanges(other))
        );
    }

    contains(el) {
        return (
            this.containerRef.el?.contains(el) ||
            [...this.children].some((child) => child.contains(el))
        );
    }

    handleChange(other) {
        if (this.shouldIgnoreChanges(other)) {
            return;
        }

        if (other.isOpen && this.isOpen) {
            this.close();
        }
    }
}

export function useDropdownNesting(state, containerRef) {
    const env = useEnv();
    const current = new DropdownNestingState({
        parent: env[DROPDOWN],
        close: () => state.close(),
        containerRef,
    });

    useChildSubEnv({ [DROPDOWN]: current });

    useBus(BUS, "state-changed", ({ detail: other }) => current.handleChange(other));

    useEffect(
        (isOpen) => {
            current.isOpen = isOpen;
        },
        () => [state.isOpen]
    );

    onWillDestroy(() => {
        current.remove();
    });

    return {
        get hasParent() {
            return Boolean(current.parent);
        },
        navigationOptions: {
            onOpen: (items) => {
                if (current.parent) {
                    items[0]?.focus();
                }
            },
            onEscape: () => current.close(),
            onArrowLeft: (index, items) => {
                if (
                    localization.direction === "rtl" &&
                    items[index]?.target.classList.contains("o-dropdown")
                ) {
                    items[index]?.select();
                } else if (current.parent) {
                    current.close();
                }
            },
            onArrowRight: (index, items) => {
                if (localization.direction === "rtl" && current.parent) {
                    current.close();
                } else if (items[index]?.target.classList.contains("o-dropdown")) {
                    items[index]?.select();
                }
            },
            onMouseEnter: (item) => {
                if (item.target.classList.contains("o-dropdown")) {
                    item.select();
                }
            },
        },
    };
}

export function useDropdownItemNesting(closingMode) {
    const env = useEnv();
    return {
        onSelected: () => {
            const dropdown = env[DROPDOWN];
            if (!dropdown) {
                return;
            }

            switch (closingMode) {
                case "closest":
                    dropdown.close();
                    break;
                case "all":
                    dropdown.closeAllParents();
                    break;
            }
        },
        onMouseEnter: () => {
            const dropdown = env[DROPDOWN];
            if (!dropdown) {
                return;
            }

            dropdown.closeChildren();
        },
    };
}
