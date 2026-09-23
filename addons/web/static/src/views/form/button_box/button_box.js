// @ts-check
/** @odoo-module native */

import { Component } from "@odoo/owl";
import { Dropdown } from "@web/components/dropdown/dropdown";
import { DropdownItem } from "@web/components/dropdown/dropdown_item";
import { useService } from "@web/core/utils/hooks";

export class ButtonBox extends Component {
    static template = "web.Form.ButtonBox";
    static components = { Dropdown, DropdownItem };
    static props = {
        slots: Object,
        class: { type: String, optional: true },
    };
    static defaultProps = {
        class: "",
    };

    setup() {
        this.ui = useService("ui");
    }

    /** @returns {{ visible: string[], additional: string[], isFull: boolean }} */
    get layout() {
        const maxVisibleButtons = [0, 0, 4, 5, 7, 8][this.ui.size] ?? 8;
        const allVisibleButtons = Object.entries(this.props.slots)
            .filter(([_, slot]) => this.isSlotVisible(slot))
            .map(([slotName]) => slotName);
        if (allVisibleButtons.length <= maxVisibleButtons) {
            return {
                visible: allVisibleButtons,
                additional: [],
                isFull: allVisibleButtons.length === maxVisibleButtons,
            };
        }
        const splitIndex = Math.max(maxVisibleButtons - 1, 0);
        return {
            visible: allVisibleButtons.slice(0, splitIndex),
            additional: allVisibleButtons.slice(splitIndex),
            isFull: true,
        };
    }

    get visibleButtons() {
        return this.layout.visible;
    }

    get additionalButtons() {
        return this.layout.additional;
    }

    get isFull() {
        return this.layout.isFull;
    }

    /**
     * @param {{ isVisible?: boolean }} slot
     * @returns {boolean}
     */
    isSlotVisible(slot) {
        return !("isVisible" in slot) || Boolean(slot.isVisible);
    }

    /** @param {MouseEvent} ev */
    activateStatButton(ev) {
        const item = /** @type {HTMLElement} */ (ev.currentTarget);
        /** @type {HTMLElement | null} */ (
            item.querySelector(".oe_stat_button")
        )?.click();
    }
}
