import { Component } from "@odoo/owl";
import { isMobileOS } from "@web/core/browser/feature_detection";

import { Dropdown } from "@web/core/dropdown/dropdown";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

/**
 * @typedef {Object} Props
 * @property {Object[]} actions
 * @property {number} maxHeight
 * @extends {Component<Props, Env>}
 */
export class AttachmentActions extends Component {
    static components = { Dropdown, DropdownItem };
    static props = ["actions", "maxHeight"];
    static template = "mail.AttachmentActions";

    setup() {
        super.setup();
        this.actionsMenuState = useDropdownState();
        this.isMobileOS = isMobileOS;
    }
}
