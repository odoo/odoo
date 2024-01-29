import { useEnvDebugContext } from "./debug_context";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

import { Component } from "@odoo/owl";

export class DebugMenuBasic extends Component {
    static template = "web.DebugMenu";
    static components = {
        Dropdown,
        DropdownItem,
    };
    static props = {};
    setup() {
        const debugContext = useEnvDebugContext();
        // Needs to be bound to this for use in template
        this.getElements = async () => {
            this.elements = await debugContext.getItems(this.env);
        };
    }
}
