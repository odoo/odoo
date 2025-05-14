import { Component } from "@odoo/owl";
import { BottomSheet } from "@web/core/bottom_sheet/bottom_sheet";

export class StatusBarBottomSheet extends Component {
    static components = { BottomSheet };
    static template = "web.StatusBarBottomSheet";
    static props = {
        items: { type: Array },
        onSelect: { type: Function },
        close: { type: Function, optional: true },
        isDisabled: { type: Boolean, optional: true },
    };

    selectItem(item) {
        if (this.props.isDisabled) return;

        if (this.props.onSelect) {
            this.props.onSelect(item);
        }
        if (this.props.close) {
            this.props.close();
        }
    }
}
