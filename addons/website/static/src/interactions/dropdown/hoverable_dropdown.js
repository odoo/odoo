import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { SIZES, utils as uiUtils } from "@web/core/ui/ui_service";

export class HoverableDropdown extends Interaction {
    static selector = "header.o_hoverable_dropdown";
    dynamicContent = {
        ".dropdown": {
            "t-on-mouseenter.withTarget": this.onMouseEnter,
            "t-on-mouseleave.withTarget": this.onMouseLeave,
        },
        ".nav:not(.o_mega_menu_is_offcanvas) .o_mega_menu": {
            "t-att-style": () => ({
                "margin-top": this.isSmall() ? "" : "0 !important",
                top: this.isSmall() ? "" : "unset",
            }),
        },
        _window: {
            "t-on-resize": this.onResize,
        },
    };

    setup() {
        this.dropdownMenuEls = this.el.querySelectorAll(".dropdown-menu");
        this.breakpointSize = SIZES.LG; // maybe need to check in .navbar elem like in BaseHeader?
    }

    start() {
        this.onResize();
    }

    isSmall() {
        return uiUtils.getSize() < this.breakpointSize;
    }

    /**
     * @param {Event} dropdownEl
     * @param {boolean} show
     */
    updateDropdownVisibility(dropdownEl, show) {
        const dropdownToggleEl = dropdownEl.querySelector(".dropdown-toggle");
        if (this.isSmall() || !dropdownToggleEl || dropdownEl.closest(".o_extra_menu_items")) {
            return;
        }
        const dropdown = Dropdown.getOrCreateInstance(dropdownToggleEl);
        show ? dropdown.show() : dropdown.hide();
    }

    /**
     * @param {MouseEvent} ev
     * @param {HTMLElement} currentTargetEl
     */
    onMouseEnter(ev, currentTargetEl) {
        const focusedEl =
            this.el.ownerDocument.querySelector(":focus") ||
            window.frameElement?.ownerDocument.querySelector(":focus");

        // The user must click on the dropdown if he is on mobile (no way to
        // hover) or if the dropdown is the (or in the) extra menu ('+').
        this.updateDropdownVisibility(currentTargetEl, true);

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
     * @param {MouseEvent} ev
     * @param {HTMLElement} currentTargetEl
     */
    onMouseLeave(ev, targelEl) {
        this.updateDropdownVisibility(targelEl, false);
    }

    onResize() {
        for (const dropdownMenuEl of this.dropdownMenuEls) {
            dropdownMenuEl.setAttribute("data-bs-popper", "none");
        }
    }
}

registry.category("public.interactions").add("website.hoverable_dropdown", HoverableDropdown);
