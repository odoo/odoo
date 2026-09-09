/** @odoo-module native */
import { makeLogger } from "@web/core/debug/debug_logger";
import { registry } from "@web/core/registry";
import { Dropdown } from "@web/libs/bootstrap";
import { Interaction } from "@web/public/interaction";
import { SIZES, utils as uiUtils } from "@web/ui/viewport";

const log = makeLogger("website.interaction.hoverable_dropdown");

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
            "t-on-resize": this.throttled(this.onResize),
        },
    };

    setup() {
        this.dropdownMenuEls = this.el.querySelectorAll(".dropdown-menu");
        this.breakpointSize = SIZES.LG;
        log.lifecycle("HoverableDropdown setup", () => ({
            menus: this.dropdownMenuEls.length,
        }));
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
        if (
            this.isSmall() ||
            !dropdownToggleEl ||
            dropdownEl.closest(".o_extra_menu_items")
        ) {
            log.logic("HoverableDropdown updateDropdownVisibility: skip", () => ({
                show,
                isSmall: this.isSmall(),
                hasToggle: !!dropdownToggleEl,
                inExtraMenu: !!dropdownEl.closest(".o_extra_menu_items"),
            }));
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

        this.updateDropdownVisibility(currentTargetEl, true);

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

registry
    .category("public.interactions")
    .add("website.hoverable_dropdown", HoverableDropdown);
