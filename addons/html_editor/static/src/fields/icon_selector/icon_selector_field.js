import { Component, onWillStart, proxy, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { SelectMenu } from "@web/core/select_menu/select_menu";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { searchIcons } from "@html_editor/main/media/media_dialog/icon_selector";

export class IconSelectorField extends Component {
    static template = "html_editor.IconSelectorField";
    static components = { SelectMenu };
    props = useProps(standardFieldProps);

    state = proxy({
        choices: [],
    });

    setup() {
        onWillStart(() => this.loadChoices());
    }

    get iconValue() {
        return this.props.record.data[this.props.name] || "";
    }

    get availableChoices() {
        if (!this.iconValue || this.state.choices.some((choice) => choice.value === this.iconValue)) {
            return this.state.choices;
        }
        return [{ value: this.iconValue, label: this.iconValue }, ...this.state.choices];
    }

    getIconName(value) {
        return value.endsWith("_f") ? value.slice(0, -2) : value;
    }

    async loadChoices() {
        const icons = await searchIcons();
        this.state.choices = icons.flatMap(({ dataIcon, hasFilledVersion }) => [
            { value: dataIcon, label: dataIcon },
            ...(hasFilledVersion ? [{ value: `${dataIcon}_f`, label: `${dataIcon}_f` }] : []),
        ]);
    }

    onSelect(value) {
        this.props.record.update({ [this.props.name]: value || false });
    }
}

export const iconSelectorField = {
    component: IconSelectorField,
    displayName: _t("Icon Selector"),
    supportedTypes: ["char"],
};

registry.category("fields").add("icon_selector", iconSelectorField);
