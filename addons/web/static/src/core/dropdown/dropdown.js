/** @odoo-module **/

import { useBus } from "../bus_hook";
import { useService } from "../service_hook";
import { scrollTo } from "../utils/scrolling";
import { ParentClosingMode } from "./dropdown_item";

const { Component, core, hooks, useState, QWeb } = owl;
const { useExternalListener, onMounted, onWillStart } = hooks;

export class Dropdown extends Component {
    setup() {
        this.state = useState({ open: this.props.startOpen, groupIsOpen: this.props.startOpen });

        this.ui = useService("ui");
        if (!this.props.manualOnly) {
            // Close on outside click listener
            useExternalListener(window, "click", this.onWindowClicked);
            // Listen to all dropdowns state changes
            useBus(Dropdown.bus, "state-changed", this.onDropdownStateChanged);
        }
        useBus(this.ui.bus, "active-element-changed", (activeElement) => {
            if (activeElement !== this.myActiveEl) {
                this.close();
            }
        });

        onMounted(() => {
            Promise.resolve().then(() => {
                this.myActiveEl = this.ui.activeElement;
            });
        });

        onWillStart(() => {
            if ((this.state.open || this.state.groupIsOpen) && this.props.beforeOpen) {
                return this.props.beforeOpen();
            }
        });
    }

    // ---------------------------------------------------------------------------
    // Private
    // ---------------------------------------------------------------------------

    async changeStateAndNotify(stateSlice) {
        if ((stateSlice.open || stateSlice.groupIsOpen) && this.props.beforeOpen) {
            await this.props.beforeOpen();
        }
        // Update the state
        Object.assign(this.state, stateSlice);
        // Notify over the bus
        Dropdown.bus.trigger("state-changed", {
            emitter: this,
            newState: { ...this.state },
        });
    }

    /**
     * @param {"PREV"|"NEXT"|"FIRST"|"LAST"} direction
     */
    setActiveItem(direction) {
        const items = [
            ...this.el.querySelectorAll(":scope > ul.o_dropdown_menu > .o_dropdown_item"),
        ];
        const prevActiveIndex = items.findIndex((item) =>
            [...item.classList].includes("o_dropdown_active")
        );
        const nextActiveIndex =
            direction === "NEXT"
                ? Math.min(prevActiveIndex + 1, items.length - 1)
                : direction === "PREV"
                ? Math.max(0, prevActiveIndex - 1)
                : direction === "LAST"
                ? items.length - 1
                : direction === "FIRST"
                ? 0
                : undefined;
        if (nextActiveIndex !== undefined) {
            items.forEach((item) => item.classList.remove("o_dropdown_active"));
            items[nextActiveIndex].classList.add("o_dropdown_active");
            scrollTo(items[nextActiveIndex], this.el.querySelector(".o_dropdown_menu"));
        }
    }

    close() {
        return this.changeStateAndNotify({ open: false, groupIsOpen: false });
    }

    open() {
        return this.changeStateAndNotify({ open: true, groupIsOpen: true });
    }

    toggle() {
        const toggled = !this.state.open;
        return this.changeStateAndNotify({
            open: toggled,
            groupIsOpen: toggled,
        });
    }

    // ---------------------------------------------------------------------------
    // Handlers
    // ---------------------------------------------------------------------------

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
     */
    onDropdownStateChanged(args) {
        if (args.emitter.el === this.el) {
            // Do not listen to my own events
            return;
        }

        if (this.el.contains(args.emitter.el)) {
            // Do not listen to events emitted by children
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

    onTogglerClick() {
        this.toggle();
    }

    onTogglerMouseEnter() {
        if (this.state.groupIsOpen && !this.state.open) {
            this.open();
        }
    }

    /**
     * Used to close ourself on outside click.
     */
    onWindowClicked(ev) {
        // Return if already closed
        if (!this.state.open) return;
        // Return if it's a different ui active element
        if (this.ui.activeElement !== this.myActiveEl) return;

        let element = ev.target;
        let gotClickedInside = false;
        do {
            element = element.parentElement && element.parentElement.closest(".o_dropdown");
            gotClickedInside = element === this.el;
        } while (element && element.parentElement && !gotClickedInside);

        if (!gotClickedInside) {
            this.close();
        }
    }
}
Dropdown.bus = new core.EventBus();
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
