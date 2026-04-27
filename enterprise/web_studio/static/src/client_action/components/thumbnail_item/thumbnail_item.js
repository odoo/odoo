/** @odoo-module */
import { Component } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";

export class ThumbnailItem extends Component {
    static defaultProps = {
        showMoreMenu: true,
        onClick: () => {},
    };
    static template = "web_studio.ThumbnailItem";
    static props = {
        className: { type: String, optional: true },
        showMoreMenu: { type: Boolean, optional: true },
        icon: { type: Object },
        onClick: { type: Function, optional: true },
        slots: true,
    };
    static components = { Dropdown };

    get hasDropdown() {
        return this.props.showMoreMenu && this.props.slots && this.props.slots.dropdown;
    }
}
