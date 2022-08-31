/** @odoo-module **/

import { useBus, useService } from "@web/core/utils/hooks";
import { usePosition } from "../position_hook";
import { useDropdownNavigation } from "./dropdown_navigation_hook";
import { localization } from "../l10n/localization";

const {
    Component,
    EventBus,
    onWillStart,
    useEffect,
    useExternalListener,
    useRef,
    useState,
    useChildSubEnv,
} = owl;

const DIRECTION_CARET_CLASS = {
    bottom: "dropdown",
    top: "dropup",
    left: "dropstart",
    right: "dropend",
};

export const DROPDOWN = Symbol("Dropdown");

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
        this.rootRef = useRef("root");

        // Set up beforeOpen ---------------------------------------------------
        onWillStart(() => {
            if (this.state.open && this.props.beforeOpen) {
                return this.props.beforeOpen();
            }
        });

        // Set up dynamic open/close behaviours --------------------------------
        if (!this.props.manualOnly) {
            // Close on outside click listener
            useExternalListener(window, "click", this.onWindowClicked, { capture: true });
            // Listen to all dropdowns state changes
            useBus(Dropdown.bus, "state-changed", ({ detail }) =>
                this.onDropdownStateChanged(detail)
            );
        }

        // Set up UI active element related behavior ---------------------------
        this.ui = useService("ui");
        useEffect(
            () => {
                Promise.resolve().then(() => {
                    this.myActiveEl = this.ui.activeElement;
                });
            },
            () => []
        );

        // Set up nested dropdowns ---------------------------------------------
        this.parentDropdown = this.env[DROPDOWN];
        useChildSubEnv({
            [DROPDOWN]: {
                close: this.close.bind(this),
                closeAllParents: () => {
                    this.close();
                    if (this.parentDropdown) {
                        this.parentDropdown.closeAllParents();
                    }
                },
            },
        });

        // Set up key navigation -----------------------------------------------
        useDropdownNavigation();

        // Set up toggler and positioning --------------------------------------
        /** @type {string} **/
        let position =
            this.props.position || (this.parentDropdown ? "right-start" : "bottom-start");
        let [direction, variant = "middle"] = position.split("-");
        if (localization.direction === "rtl") {
            if (["bottom", "top"].includes(direction)) {
                variant = variant === "start" ? "end" : "start";
            } else {
                direction = direction === "left" ? "right" : "left";
            }
            position = [direction, variant].join("-");
        }
        const positioningOptions = {
            popper: "menuRef",
            position,
            onPositioned: (el, { direction, variant }) => {
                if (this.parentDropdown && ["right", "left"].includes(direction)) {
                    // Correctly align sub dropdowns items with its parent's
                    if (variant === "start") {
                        el.style.marginTop = "calc(-.5rem - 1px)";
                    } else if (variant === "end") {
                        el.style.marginTop = "calc(.5rem - 2px)";
                    }
                }
            },
        };
        this.directionCaretClass = DIRECTION_CARET_CLASS[direction];
        this.togglerRef = useRef("togglerRef");
        if (this.props.toggler === "parent") {
            // Add parent click listener to handle toggling
            useEffect(
                () => {
                    const onClick = (ev) => {
                        if (this.rootRef.el.contains(ev.target)) {
                            // ignore clicks inside the dropdown
                            return;
                        }
                        this.toggle();
                    };
                    this.rootRef.el.parentElement.addEventListener("click", onClick);
                    return () => {
                        this.rootRef.el.parentElement.removeEventListener("click", onClick);
                    };
                },
                () => []
            );

            // Position menu relatively to parent element
            usePosition(() => this.rootRef.el.parentElement, positioningOptions);
        } else {
            // Position menu relatively to inner toggler
            const togglerRef = useRef("togglerRef");
            usePosition(() => togglerRef.el, positioningOptions);
        }
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
        if (stateSlice.open && this.props.beforeOpen) {
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
        if (this.rootRef.el.contains(args.emitter.rootRef.el)) {
            // Do not listen to events emitted by self or children
            return;
        }

        // Emitted by direct siblings ?
        if (args.emitter.rootRef.el.parentElement === this.rootRef.el.parentElement) {
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
     * Opens the dropdown the mouse enters its toggler.
     * NB: only if its siblings dropdown group is opened and if not a sub dropdown.
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

        if (ev.target.closest(".bootstrap-datetimepicker-widget")) {
            return;
        }

        // Close if we clicked outside the dropdown, or outside the parent
        // element if it is the toggler
        const rootEl =
            this.props.toggler === "parent" ? this.rootRef.el.parentElement : this.rootRef.el;
        const gotClickedInside = rootEl.contains(ev.target);
        if (!gotClickedInside) {
            this.close();
        }
    }
}
Dropdown.bus = new EventBus();
Dropdown.props = {
    class: {
        type: String,
        optional: true,
    },
    toggler: {
        type: String,
        optional: true,
        validate: (prop) => ["parent"].includes(prop),
    },
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
    tooltip: {
        type: String,
        optional: true,
    },
    title: {
        type: String,
        optional: true,
    },
    position: {
        type: String,
        optional: true,
    },
    slots: {
        type: Object,
        optional: true,
    },
};
Dropdown.template = "web.Dropdown";
