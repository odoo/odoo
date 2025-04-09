import { Component } from "@odoo/owl";

/**
 * Content component for the status bar bottom sheet
 * This component displays the list of status items in a bottom sheet
 */
export class StatusBarBottomSheet extends Component {
    static template = "web.StatusBarBottomSheet";
    static props = {
        items: { type: Array },
        onSelect: { type: Function },
        close: { type: Function, optional: true },
    };

    selectItem(item) {
        if (this.props.onSelect) {
            this.props.onSelect(item);
        }
        if (this.props.close) {
            this.props.close();
        }
    }
}
