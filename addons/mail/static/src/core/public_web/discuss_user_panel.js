import { Component, useState } from "@odoo/owl";
import { ImStatus } from "../common/im_status";
import { useService } from "@web/core/utils/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

export class DiscussUserPanel extends Component {
    static template = "mail.DiscussUserPanel";
    static props = [];
    static components = { Dropdown, DropdownItem, ImStatus };

    setup() {
        super.setup();
        this.store = useState(useService("mail.store"));
    }
}
