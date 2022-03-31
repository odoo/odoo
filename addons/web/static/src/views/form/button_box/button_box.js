/** @odoo-module  */

import { useService } from "@web/core/utils/hooks";
import { Dropdown} from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

export class ButtonBox extends owl.Component {

    setup() {
        const ui = useService("ui");
        this.getMaxButtons = () => [2, 2, 2, 4, 7][ui.size] || 8;
    }

    getButtons() {
        const maxVisibleButtons = this.getMaxButtons();
        const visible = [];
        const additional = [];
        for (const [slotName, slot] of Object.entries(this.props.slots)) {
            if (!("isVisible" in slot) || slot.isVisible) {
                if (visible.length >= maxVisibleButtons) {
                    additional.push(slotName);
                } else {
                    visible.push(slotName);
                }

            }
        }
        return {visible, additional};
    }
}
ButtonBox.template = "web.Form.ButtonBox";
ButtonBox.components = { Dropdown, DropdownItem };
