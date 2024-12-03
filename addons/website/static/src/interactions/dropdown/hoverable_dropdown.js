import { Interaction } from "@website/core/interaction";
import { registry } from "@web/core/registry";

import { SIZES, utils as uiUtils } from "@web/core/ui/ui_service";

export class HoverableDropdown extends Interaction {
    static selector = "header.o_hoverable_dropdown";
    dynamicContent = {
        ".dropdown": {
            "t-on-mouseenter": this.onMouseEnter,
            "t-on-mouseleave": this.onMouseLeave,
        },
        _window: {
            "t-on-resize": this.onResize,
        },
    };

    setup() {
        this.dropdownMenuEls = this.el.querySelectorAll(".dropdown-menu");
        this.dropdownToggleEls = this.el.querySelectorAll(".dropdown-toggle");
    }

    start() {
        this.onResize();
    }

    /**
     * @param {Event} ev
     * @param {boolean} show
     */
    updateDropdownVisibility(ev, show) {
        const dropdownToggleEl = ev.currentTarget.querySelector(".dropdown-toggle");
        if (
            !dropdownToggleEl
            || uiUtils.getSize() < SIZES.LG
            || ev.currentTarget.closest(".o_extra_menu_items")
        ) {
            return;
        }
        const dropdown = Dropdown.getOrCreateInstance(dropdownToggleEl);
        show ? dropdown.show() : dropdown.hide();
    }

    /**
     * @param {Event} ev
     */
    onMouseEnter(ev) {
        const focusedEl = this.el.ownerDocument.querySelector(":focus")
            || window.frameElement?.ownerDocument.querySelector(":focus");

        // The user must click on the dropdown if he is on mobile (no way to
        // hover) or if the dropdown is the (or in the) extra menu ('+').
        this.updateDropdownVisibility(ev, true);

        // Keep the focus on the previously focused element if any, otherwise do
        // not focus the dropdown on hover.
        if (focusedEl) {
            focusedEl.focus({ preventScroll: true });
        } else {
            const dropdownToggleEl = ev.currentTarget.querySelector(".dropdown-toggle");
            if (dropdownToggleEl) {
                dropdownToggleEl.blur();
            }
        }
    }

    /**
     * @param {Event} ev
     */
    onMouseLeave(ev) {
        this.updateDropdownVisibility(ev, false);
    }

    onResize() {
        const isSmall = uiUtils.getSize() < SIZES.LG;
        for (const dropdownMenuEl of this.dropdownMenuEls) {
            dropdownMenuEl.setAttribute("data-bs-popper", "none");
            dropdownMenuEl.setAttribute("margin-top", isSmall ? "" : "0");
            dropdownMenuEl.setAttribute("top", isSmall ? "" : "unset");
        }
    }
}

registry
    .category("website.active_elements")
    .add("website.hoverable_dropdown", HoverableDropdown);
