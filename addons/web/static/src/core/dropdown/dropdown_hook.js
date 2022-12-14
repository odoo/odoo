/** @odoo-module **/

import { useState, useRef, useEffect, onWillDestroy } from "@odoo/owl";
import { usePosition } from "../position_hook";
import { useService } from "../utils/hooks";
import { localization } from "../l10n/localization";
import { useDropdownHookNavigation } from "./dropdown_hook_navigation";

export const DROPDOWN = Symbol("Dropdown");

class DropdownHook {
    constructor(properties) {
        for (const key in properties) {
            this[key] = properties[key];
        }

        this.isOpen = false;

        this.dropdownService = useService("dropdown");
        this.id = this.dropdownService.add(this);
        onWillDestroy(() => this.dropdownService.remove(this.id));

        this.menuRef = useRef(this.menuRefName);
        this.togglerRef = useRef(this.togglerRefName);

        useEffect(
            (el) => {
                if (el) {
                    // FIX: Maybe find a more proper solution for styling the container
                    el.classList.add("o-dropdown--menu", "dropdown-menu", "d-block");
                    this.onOpened();
                }
            },
            () => [this.menuRef.el]
        );

        // Set positioning ----------------------------------------------------
        /** @type {string} **/
        let [direction, variant = "middle"] = this.position.split("-");
        if (localization.direction === "rtl") {
            if (["bottom", "top"].includes(direction)) {
                variant = variant === "start" ? "end" : "start";
            } else {
                direction = direction === "left" ? "right" : "left";
            }
            this.position = [direction, variant].join("-");
        }
        const positioningOptions = {
            popper: this.menuRefName,
            position: this.position,
            onPositioned: (el, { direction, variant }) => {
                this.onPositioned({ direction, variant });
            },
        };
        usePosition(() => this.togglerRef.el, positioningOptions);

        // Set up key navigation -----------------------------------------------
        useDropdownHookNavigation(this);
    }

    updateState(isOpen) {
        this.isOpen = isOpen;
    }

    open() {
        this.beforeOpen();
        this.dropdownService.open(this.id);
    }

    close() {
        this.dropdownService.close(this.id);
    }

    toggle() {
        if (this.isOpen) {
            this.close();
        } else {
            this.open();
        }
    }

    onWindowClicked(ev) {
        // Return if already closed
        if (!this.isOpen) {
            return;
        }

        // TODO: Return if it's a different ui active element
        // if (this.ui.activeElement !== this.myActiveEl) {
        //     return;
        // }

        // Close if we clicked outside the dropdown, or outside the parent
        // element if it is the toggler
        const rootEl = this.menuRef.el;
        if (rootEl) {
            const gotClickedInside = rootEl.contains(ev.target);
            if (!gotClickedInside) {
                this.close();
            }
        }
    }
}

export function useDropdown({
    menuRefName,
    togglerRefName,
    position = "bottom-fit",
    onPositioned = () => {},
    beforeOpen = () => {},
    onOpened = () => {},
}) {
    const dropdown = new DropdownHook({
        menuRefName,
        togglerRefName,
        position,
        onPositioned,
        beforeOpen,
        onOpened,
    });
    return useState(dropdown);
}
