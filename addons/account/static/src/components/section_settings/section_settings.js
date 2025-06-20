import { _t } from "@web/core/l10n/translation";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { Component } from "@odoo/owl";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { registry } from '@web/core/registry';

export class SectionSettings extends Component {
    static template = "account.SectionSettings";
    static props = {
        ...standardWidgetProps,
    };
    static components = {
        Dropdown,
        DropdownItem,
    };

    setup() {
        super.setup();
        this.actions = [
            {
                id: "line_add",
                label: _t("Add Line"),
                icon: "fa fa-plus",
                visible: true,
                sequence: 10,
                onSelected: () => this.onLineAdd(),
            },
            {
                id: "subsection_add",
                label: _t("Add Subsection"),
                icon: "fa fa-folder",
                visible: this.props.record.data.display_type === "line_section",
                sequence: 20,
                onSelected: () => this.onSubsectionAdd(),
            },
            {
                id: "price_hide",
                label: this.props.record.data.show_section_line_amount ? _t("Hide Prices") : _t("Show Prices"),
                icon: this.props.record.data.show_section_line_amount ? "fa fa-eye-slash" : "fa fa-eye",
                visible: true,
                sequence: 30,
                onSelected: async () => await this.onPricesToggle(),
            },
            {
                id: "composition_hide",
                label: this.props.record.data.show_composition ? _t("Hide Composition") : _t("Show Composition"),
                icon: this.props.record.data.show_composition ? "fa fa-eye-slash" : "fa fa-eye",
                visible: true,
                sequence: 40,
                onSelected: async () => await this.onCompositionToggle(),
            },
            {
                id: "section_up",
                label: _t("Move Up"),
                icon: "fa fa-arrow-up",
                visible: true,
                sequence: 50,
                onSelected: async () => await this.env.onSectionMoveUp(this.props.record),
            },
            {
                id: "section_down",
                label: _t("Move Down"),
                icon: "fa fa-arrow-down",
                visible: true,
                sequence: 60,
                onSelected: async () => await this.env.onSectionMoveDown(this.props.record)
            },
            {
                id: "section_duplicate",
                label: _t("Duplicate"),
                icon: "fa fa-copy",
                visible: true,
                sequence: 70,
                onSelected: async () => await this.env.onSectionDuplicate(this.props.record),
            },
            {
                id: "section_delete",
                label: _t("Delete"),
                icon: "fa fa-trash",
                visible: true,
                sequence: 80,
                onSelected: async () => await this.env.onSectionDelete(this.props.record),
            },
        ]
    }

    onLineAdd() {
        alert("Please Wait I am Working On it 😓");
    }

    onSubsectionAdd() {
        alert("Please Wait I am Working On it 😓");
    }

    async onPricesToggle() {
        const changes = { show_section_line_amount: !this.props.record.data.show_section_line_amount };
        await this.props.record.update(changes, { save: true });
    }

    async onCompositionToggle() {
        const changes = { show_composition: !this.props.record.data.show_composition };
        await this.props.record.update(changes, { save: true });
    }

    onDuplicate() {
        alert("Please Wait I am Working On it 😓");
    }

    get sortedActions() {
        return this.actions.sort((a, b) => a.sequence - b.sequence);
    }
}

export const sectionSettingsWidget = {
    component: SectionSettings,
    listViewWidth: 20,
};

registry.category("view_widgets").add("section_settings", sectionSettingsWidget);
