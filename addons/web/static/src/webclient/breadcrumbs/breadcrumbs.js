import { Component } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useService } from "@web/core/utils/hooks";

export class Breadcrumbs extends Component {
    static template = "web.Breadcrumbs";
    static components = { Dropdown, DropdownItem };
    static props = {
        breadcrumbs: Array,
        slots: { type: Object, optional: true },
    };

    setup() {
        this.actionService = useService("action");
    }

    /**
     * Called when an element of the breadcrumbs is clicked.
     *
     * @param {string} jsId
     */
    onBreadcrumbClicked(jsId) {
        this.actionService.restore(jsId);
    }
}
