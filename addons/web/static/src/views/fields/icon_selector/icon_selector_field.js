import { Component, computed, useProps } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { IconSelector } from "@html_editor/main/media/media_dialog/icon_selector";
import { standardFieldProps } from "../standard_field_props";

export class IconSelectorField extends Component {
    static template = "web.IconSelectorField";
    static components = { Dropdown, IconSelector };
    props = useProps(standardFieldProps);

    dropdown = useDropdownState();
    selectedMedia = computed(() => {
        const selectedIcon = this.selectedIcon;
        if (!selectedIcon) {
            return { icons: [] };
        }
        return {
            icons: [selectedIcon],
        };
    });

    get iconValue() {
        return this.props.record.data[this.props.name] || "";
    }

    get selectedIcon() {
        if (!this.iconValue) {
            return null;
        }
        const filled = this.iconValue.endsWith("_f");
        const dataIcon = filled ? this.iconValue.slice(0, -2) : this.iconValue;
        return {
            id: dataIcon,
            name: dataIcon,
            dataIcon,
            filled,
        };
    }

    async onIconSelect({ dataIcon, filled }) {
        const value = `${dataIcon}${filled ? "_f" : ""}`;
        await this.props.record.update({ [this.props.name]: value });
        this.dropdown.close();
    }

    async clearIcon() {
        await this.props.record.update({ [this.props.name]: false });
    }
}

export const iconSelectorField = {
    component: IconSelectorField,
    displayName: _t("Icon Selector"),
    supportedTypes: ["char"],
};

registry.category("fields").add("icon_selector", iconSelectorField);
