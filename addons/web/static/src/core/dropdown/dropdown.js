/** @odoo-module **/

import { useBus } from "../bus_hook";
import { useService } from "../service_hook";
import { useEffect } from "../effect_hook";
import { scrollTo } from "../utils/scrolling";
import { ParentClosingMode } from "./dropdown_item";

const { Component, core, hooks, useState, QWeb } = owl;
const { EventBus } = core;
const { useExternalListener, onWillStart } = hooks;

/**
 * @typedef DropdownState
 * @property {boolean} open
 * @property {boolean} groupIsOpen
 */

/**
 * @typedef DropdownStateChangedPayload
 * @property {Dropdown} emitter
 * @property {DropdownState} newState
 */

/**
 * @extends Component
 */
export class Dropdown extends Component {
    setup() {
        this.state = useState({
            open: this.props.startOpen,
            groupIsOpen: this.props.startOpen,
        });

        onWillStart(() => {
            if ((this.state.open || this.state.groupIsOpen) && this.props.beforeOpen) {
                return this.props.beforeOpen();
            }
        });

        if (!this.props.manualOnly) {
            // Close on outside click listener
            useExternalListener(window, "click", this.onWindowClicked);
            // Listen to all dropdowns state changes
            useBus(Dropdown.bus, "state-changed", this.onDropdownStateChanged);
        }

        // Set up UI active element related behavior ---------------------------
        this.ui = useService("ui");
        useBus(this.ui.bus, "active-element-changed", (activeElement) => {
            if (activeElement !== this.myActiveEl && !this.state.open) {
                // Close when UI active element changes to something different
                this.close();
            }
        });
        useEffect(() => {
            Promise.resolve().then(() => {
                this.myActiveEl = this.ui.activeElement;
            });
        }, () => []);

        // Set up key navigation -----------------------------------------------
        this.hotkeyService = useService("hotkey");
        this.hotkeyRemoves = [];

        const nextActiveIndexFns = {
            "FIRST": () => 0,
            "LAST": (items) => items.length - 1,
            "NEXT": (items, prevActiveIndex) => Math.min(prevActiveIndex + 1, items.length - 1),
            "PREV": (_, prevActiveIndex) => Math.max(0, prevActiveIndex - 1),
        };

        /** @type {(direction: "FIRST"|"LAST"|"NEXT"|"PREV") => Function} */
        function activeItemSetter(direction) {
            return function () {
                const items = [...this.el.querySelectorAll(":scope > ul.o_dropdown_menu > .o_dropdown_item")];
                const prevActiveIndex = items.findIndex((item) =>
                    [...item.classList].includes("o_dropdown_active")
                );
                const nextActiveIndex = nextActiveIndexFns[direction](items, prevActiveIndex);
                items.forEach((item) => item.classList.remove("o_dropdown_active"));
                items[nextActiveIndex].classList.add("o_dropdown_active");
                scrollTo(items[nextActiveIndex], this.el.querySelector(".o_dropdown_menu"));
            };
        }

        const hotkeyCallbacks = {
            "arrowdown": activeItemSetter("NEXT").bind(this),
            "arrowup": activeItemSetter("PREV").bind(this),
            "shift+arrowdown": activeItemSetter("LAST").bind(this),
            "shift+arrowup": activeItemSetter("FIRST").bind(this),
            "enter": () => {
                const activeItem = this.el.querySelector(
                    ":scope > ul.o_dropdown_menu > .o_dropdown_item.o_dropdown_active"
                );
                if (activeItem) {
                    activeItem.click();
                }
            },
            "escape": this.close.bind(this),
        };

        /** @this {Dropdown} */
        function autoSubscribeKeynav() {
            if (this.state.open) {
                // Subscribe keynav
                if (this.hotkeyRemoves.length) {
                    // Keynav already subscribed
                    return;
                }
                for (const [hotkey, callback] of Object.entries(hotkeyCallbacks)) {
                    this.hotkeyRemoves.push(
                        this.hotkeyService.add(hotkey, callback, {
                            altIsOptional: true,
                            allowRepeat: true,
                        })
                    );
                }
            } else {
                // Unsubscribe keynav
                for (const removeHotkey of this.hotkeyRemoves) {
                    removeHotkey();
                }
                this.hotkeyRemoves = [];
            }
        }

        useEffect(autoSubscribeKeynav.bind(this));
    }

    // -------------------------------------------------------------------------
    // Private
    // -------------------------------------------------------------------------

    /**
     * Changes the dropdown state and notifies over the Dropdown bus.
     *
     * All state changes must trigger on the bus, except when reacting to
     * another dropdown state change.
     *
     * @see onDropdownStateChanged()
     *
     * @param {Partial<DropdownState>} stateSlice
     */
    async changeStateAndNotify(stateSlice) {
        if ((stateSlice.open || stateSlice.groupIsOpen) && this.props.beforeOpen) {
            await this.props.beforeOpen();
        }
        // Update the state
        Object.assign(this.state, stateSlice);
        // Notify over the bus
        /** @type DropdownStateChangedPayload */
        const stateChangedPayload = {
            emitter: this,
            newState: { ...this.state },
        };
        Dropdown.bus.trigger("state-changed", stateChangedPayload);
    }

    /**
     * Closes the dropdown.
     *
     * @returns {Promise<void>}
     */
    close() {
        return this.changeStateAndNotify({ open: false, groupIsOpen: false });
    }

    /**
     * Opens the dropdown.
     *
     * @returns {Promise<void>}
     */
    open() {
        return this.changeStateAndNotify({ open: true, groupIsOpen: true });
    }

    /**
     * Toggles the dropdown open state.
     *
     * @returns {Promise<void>}
     */
    toggle() {
        const toggled = !this.state.open;
        return this.changeStateAndNotify({ open: toggled, groupIsOpen: toggled });
    }

    // -------------------------------------------------------------------------
    // Handlers
    // -------------------------------------------------------------------------

    /**
     * Checks if should close on dropdown item selection.
     *
     * @param {CustomEvent<import("./dropdown_item").DropdownItemSelectedEventDetail>} ev
     */
    onItemSelected(ev) {
        // Handle parent closing request
        const { dropdownClosingRequest } = ev.detail;
        const closeAll = dropdownClosingRequest.mode === ParentClosingMode.AllParents;
        const closeSelf =
            dropdownClosingRequest.isFresh &&
            dropdownClosingRequest.mode === ParentClosingMode.ClosestParent;
        if (!this.props.manualOnly && (closeAll || closeSelf)) {
            this.close();
        }
        // Mark closing request as started
        ev.detail.dropdownClosingRequest.isFresh = false;
    }

    /**
     * Dropdowns react to each other state changes through this method.
     *
     * All state changes must trigger on the bus, except when reacting to
     * another dropdown state change.
     *
     * @see changeStateAndNotify()
     *
     * @param {DropdownStateChangedPayload} args
     */
    onDropdownStateChanged(args) {
        if (this.el.contains(args.emitter.el)) {
            // Do not listen to events emitted by self or children
            return;
        }

        // Emitted by direct siblings ?
        if (args.emitter.el.parentElement === this.el.parentElement) {
            // Sync the group status
            this.state.groupIsOpen = args.newState.groupIsOpen;

            // Another dropdown is now open ? Close myself without notifying siblings.
            if (this.state.open && args.newState.open) {
                this.state.open = false;
            }
        } else {
            // Another dropdown is now open ? Close myself and notify the world (i.e. siblings).
            if (this.state.open && args.newState.open) {
                this.close();
            }
        }
    }

    /**
     * Toggles the dropdown on its toggler click.
     */
    onTogglerClick() {
        this.toggle();
    }

    /**
     * Opens the dropdown the mous enters its toggler.
     * NB: only if its siblings dropdown group is opened.
     */
    onTogglerMouseEnter() {
        if (this.state.groupIsOpen && !this.state.open) {
            this.open();
        }
    }

    /**
     * Used to close ourself on outside click.
     *
     * @param {MouseEvent} ev
     */
    onWindowClicked(ev) {
        // Return if already closed
        if (!this.state.open) {
            return;
        }
        // Return if it's a different ui active element
        if (this.ui.activeElement !== this.myActiveEl) {
            return;
        }

        const gotClickedInside = this.el.contains(ev.target);
        if (!gotClickedInside) {
            this.close();
        }
    }
}
Dropdown.bus = new EventBus();
Dropdown.props = {
    startOpen: {
        type: Boolean,
        optional: true,
    },
    manualOnly: {
        type: Boolean,
        optional: true,
    },
    menuClass: {
        type: String,
        optional: true,
    },
    beforeOpen: {
        type: Function,
        optional: true,
    },
    togglerClass: {
        type: String,
        optional: true,
    },
    hotkey: {
        type: String,
        optional: true,
    },
    title: {
        type: String,
        optional: true,
    },
};
Dropdown.template = "web.Dropdown";

QWeb.registerComponent("Dropdown", Dropdown);
