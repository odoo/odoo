import { Component } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { _t } from "@web/core/l10n/translation";

export class SectionDropdown extends Component {
    static template = "account.SectionDropdown";
    static components = { Dropdown, DropdownItem };

    static props = { section: Object };

    get dropdownItems() {
        const items = [
            {
                label: _t("Rename"),
                action: () => this.env.enableRenameSectionInput(this.props.section),
                iconClass: "fa fa-fw fa-pencil",
            },
            {
                label: _t("Duplicate"),
                action: () => this.env.duplicateSection(this.props.section),
                iconClass: "fa fa-fw fa-clone",
            },
            {
                label: _t("Delete"),
                action: () => this.env.deleteSection(this.props.section),
                class: "text-danger",
                iconClass: "fa fa-fw fa-trash",
            },
        ];
        if (!this.props.section.parent_id) {
            items.unshift({
                label: _t("Add a subsection"),
                action: () => this.env.enableSectionInput(this.props.section.id),
                iconClass: "fa fa-fw fa-level-down",
            });
        }

        return items;
    }
}
