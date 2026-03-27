import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";

const cogMenuRegistry = registry.category("cogMenu");

export class ExportCogMenu extends Component {

    static template = "hr_work_entry.ExportCogMenu";
    static components = { Dropdown, DropdownItem };
    static props = {};

}

cogMenuRegistry.add(
    "export-cog-menu",
    {
        Component: ExportCogMenu,
        groupNumber: 40,
        isDisplayed: () => false,               // overridden by exports modules
    },
    { sequence: 1 }
);
