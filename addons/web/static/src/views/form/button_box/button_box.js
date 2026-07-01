import { useService } from "@web/core/utils/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

import { Component, computed, props, t } from "@odoo/owl";
export class ButtonBox extends Component {
    static template = "web.Form.ButtonBox";
    static components = { Dropdown, DropdownItem };
    props = props({
        slots: t.object(),
        class: t.string().optional(""),
    });

    setup() {
        this.ui = useService("ui");
    }

    buttonLayout = computed(() => {
        const maxVisibleButtons = [0, 0, 7, 4, 5, 8][this.ui.size] ?? 8;
        const allVisibleButtons = Object.entries(this.props.slots)
            .filter(([_, slot]) => this.isSlotVisible(slot))
            .map(([slotName]) => slotName);
        if (allVisibleButtons.length <= maxVisibleButtons) {
            return {
                visibleButtons: allVisibleButtons,
                additionalButtons: [],
                isFull: allVisibleButtons.length === maxVisibleButtons,
            };
        }
        // -1 for "More" dropdown
        const splitIndex = Math.max(maxVisibleButtons - 1, 0);
        return {
            visibleButtons: allVisibleButtons.slice(0, splitIndex),
            additionalButtons: allVisibleButtons.slice(splitIndex),
            isFull: true,
        };
    });

    get visibleButtons() {
        return this.buttonLayout().visibleButtons;
    }

    get additionalButtons() {
        return this.buttonLayout().additionalButtons;
    }

    get isFull() {
        return this.buttonLayout().isFull;
    }

    isSlotVisible(slot) {
        return !("isVisible" in slot) || slot.isVisible;
    }
}
