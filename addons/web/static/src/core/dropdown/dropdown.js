/** @odoo-module **/

import { Component, onMounted, onRendered, status, useEffect, useState, xml } from "@odoo/owl";
import { useNavigation } from "@web/core/navigation/navigation";
import { useChildRef, useService } from "@web/core/utils/hooks";
import { useDropdownGroup } from "./dropdown_behaviours/dropdown_group_hook";
import { useDropdownNesting } from "./dropdown_behaviours/dropdown_nesting";
import { DropdownPopover } from "./dropdown_behaviours/dropdown_popover";
import { effect } from "@web/core/utils/reactive";
import { mergeClasses } from "../utils/className";

/**
 * @typedef {Object} DropdownState
 * @property {() => void} open
 * @property {() => void} close
 * @property {() => void} toggle
 * @property {boolean} isOpen
 * @property {'auto'|'controlled'} mode
 */

/**
 * Hook used to interact with the Dropdown state.
 *
 * @param {Object} [options] - options
 *
 * @param {'auto'|'controlled'} [mode='auto'] - By default ('auto') the state
 * is managed by the dropdown, meaning click events on the toggler will open
 * the dropdown.
 * When set to 'controlled', no listener is added and it's the parent's
 * responsability to open the dropdown.
 *
 * @param {Function} [beforeOpen=undefined] - Callback invoked before opening
 * the dropdown, this can be an asynchronous function.
 *
 * @param {Function} [onChange=undefined] - Callback invoked when the state
 * changes, takes (isOpen) as its parameter.
 *
 * @returns {DropdownState}
 */
export function useDropdown({ mode, beforeOpen, onChange } = {}) {
    const state = useState({
        mode: mode || "auto",
        isOpen: false,
        open: async () => {
            if (beforeOpen) {
                await beforeOpen();
            }
            state.isOpen = true;
            onChange?.(true);
        },
        close: () => {
            state.isOpen = false;
            onChange?.(false);
        },
        toggle: async () => {
            if (state.isOpen) {
                state.close();
            } else {
                await state.open();
            }
        },
    });
    return state;
}

function getFirstElementOfNode(node) {
    if (!node) {
        return null;
    }
    if (node.el) {
        return node.el.nodeType === Node.ELEMENT_NODE ? node.el : null;
    }
    if (node.bdom || node.child) {
        return getFirstElementOfNode(node.bdom || node.child);
    }
    if (node.children) {
        for (const child of node.children) {
            const el = getFirstElementOfNode(child);
            if (el) {
                return el;
            }
        }
    }
    return null;
}

/**
 * The Dropdown component is a menu with a button that
 * will show the users actions or options to choose from.
 *
 * Items are defined using DropdownItems. Dropdowns are
 * also allowed as items to be able to create nested
 * dropdown menus.
 */
export class Dropdown extends Component {
    static template = xml`<t t-slot="default"/>`;
    static components = {};
    static props = {
        menuClass: { optional: true },
        position: { type: String, optional: true },
        slots: {
            type: Object,
            shape: {
                default: { optional: true },
                content: { optional: true },
            },
        },

        items: {
            optional: true,
            type: Array,
            elements: {
                type: Object,
                shape: {
                    label: String,
                    onSelected: Function,
                    class: { optional: true },
                    "*": true,
                },
            },
        },

        /* To be used with useChildRef */
        menuRef: { type: Function, optional: true },

        onOpened: { type: Function, optional: true },
        beforeOpen: { type: Function, optional: true },
        options: { type: Object, optional: true },

        // Manual State Handling
        state: {
            type: Object,
            shape: {
                isOpen: Boolean,
                close: Function,
                open: Function,
                "*": true,
            },
            optional: true,
        },
    };
    static defaultProps = {
        menuClass: "",
        options: {
            navigation: {},
            popover: {},
        },
        state: undefined,
    };

    setup() {
        this.popover = useService("popover");
        this.menuRef = useChildRef();
        this.props.menuRef?.(this.menuRef);
        this.renderRef = {};
        this.state = this.props.state || useDropdown({ beforeOpen: this.props.beforeOpen });
        this.nesting = useDropdownNesting(this.state, this.menuRef);
        this.group = useDropdownGroup();
        this.navigation = useNavigation(this.menuRef, {
            itemsSelector: ":scope .o-navigable, :scope .o-dropdown",
            focusInitialElementOnDisabled: () => !this.group.isInGroup,
            ...this.nesting.navigationOptions,
            ...this.props.options.navigation,
        });

        onRendered(() => this.renderRef.render?.());
        onMounted(() => this.handleStateChange(this.state));
        effect((state) => this.handleStateChange(state), [this.state]);

        useEffect(
            (target) => this.setTargetElement(target),
            () => [this.target]
        );

        useEffect(
            (enabled) => {
                if (!enabled) {
                    this.closePopover();
                }
            },
            () => [this.props.enabled]
        );
    }

    get hasParent() {
        return this.nesting.hasParent;
    }

    get target() {
        const target = getFirstElementOfNode(this.__owl__.bdom);
        if (target) {
            return target;
        } else {
            throw new Error(
                "Could not find a valid dropdown toggler, prefer a single html element and put any dynamic content inside of it."
            );
        }
    }

    get isControlled() {
        return this.props.state && this.props.state.mode == "controlled";
    }

    setTargetElement(target) {
        if (!target) {
            return;
        }
        target.ariaExpanded = false;

        const tagName = target.tagName.toLowerCase();
        target.classList.add("o-dropdown");

        if (!["input", "textarea", "table", "thead", "tbody", "tr", "th", "td"].includes(tagName)) {
            target.classList.add("dropdown-toggle");
            if (this.hasParent) {
                target.classList.add(
                    "o-dropdown-item",
                    "o-dropdown-caret",
                    "o-navigable",
                    "dropdown-item"
                );
            }
        }

        if (this.hasParent) {
            target.classList.add("o-dropdown--has-parent");
        }

        if (!this.isControlled) {
            target.addEventListener("click", this.handleClick.bind(this));
            target.addEventListener("mouseenter", this.handleMouseEnter.bind(this));

            return () => {
                target.removeEventListener("click", this.handleClick.bind(this));
                target.removeEventListener("mouseenter", this.handleMouseEnter.bind(this));
            };
        }
    }

    handleStateChange(state) {
        if (state.isOpen) {
            this.openPopover();
        } else if (!state.isOpen) {
            this.closePopover();
        }
    }

    async handleClick(event) {
        if (!this.props.enabled) {
            return;
        }

        event.stopPropagation();
        if (this.hasParent) {
            await this.state.open();
        } else {
            if (this.state.isOpen) {
                await this.state.close();
            } else {
                await this.state.open();
            }
        }
    }

    async handleMouseEnter() {
        if (this.hasParent || this.group.isOpen) {
            this.target.focus();
            await this.state.open();
        }
    }

    async openPopover() {
        if (this._closePopover !== undefined || status(this) !== "mounted") {
            return;
        }
        if (!this.target || !this.target.isConnected) {
            this.state.close();
            return;
        }

        const props = {
            onOpened: () => this.onOpened(),
            onClosed: () => this.onClosed(),
            close: () => this.state.close(),
            env: this.__owl__.childEnv,
            renderRef: this.renderRef,
            items: this.props.items,
            slots: this.props.slots,
        };

        const options = {
            popoverClass: mergeClasses("o-dropdown--menu dropdown-menu", this.props.menuClass),
            popoverRole: "menu",
            enableArrow: false,
            closeOnEscape: false, // Handled via navigation and prevents closing root of nested dropdown
            position: this.props.position || (this.hasParent ? "right-start" : "bottom-start"),
            ref: this.menuRef,
            closeOnClickAway: (target) => this.closeOnClickAway(target),
        };

        this._closePopover = this.popover.add(this.target, DropdownPopover, props, options);
        this.renderRef.render?.();
    }

    closePopover() {
        if (this._closePopover) {
            this._closePopover();
            this._closePopover = undefined;
        }
    }

    onOpened() {
        this.props.onOpened?.();
        this.navigation.enable();
        if (this.target) {
            this.target.ariaExpanded = true;
            this.target.classList.add("o-dropdown--open");
        }
    }

    onClosed() {
        this.navigation.disable();
        if (this.target) {
            this.target.ariaExpanded = false;
            this.target.classList.remove("o-dropdown--open");
        }
    }

    closeOnClickAway(target) {
        if (
            !this.target.contains(target) &&
            !this.menuRef.el.contains(target) &&
            !this.isNestedDropdown(target)
        ) {
            this.state.close();
        }
        return false;
    }

    isNestedDropdown(el) {
        let parentPopover = el.closest("[data-popover-id]");
        while (parentPopover) {
            const target = this.target.parentElement.querySelector(
                `[data-popover-for="${parentPopover.dataset.popoverId}"]`
            );
            if (this.menuRef.el.contains(target)) {
                return true;
            } else {
                parentPopover = target?.closest("[data-popover-id]");
            }
        }
        return false;
    }
}
