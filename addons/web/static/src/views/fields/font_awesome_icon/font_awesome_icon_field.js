import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { SelectMenu } from "@web/core/select_menu/select_menu";
import { hasTouch } from "@web/core/browser/feature_detection";
import { getFontAwesomeIcons } from "@web/views/utils"
import { standardFieldProps } from "../standard_field_props";

export class FontAwesomeIconField extends Component {
    static template = "web.FontAwesomeIconField";
    static components = { SelectMenu };
    static props = {
        ...standardFieldProps,
    };

    setup() {
        this.ICONS = getFontAwesomeIcons();
    }

    get choices() {
        return this.ICONS.map(icon => ({
            value: icon.className,
            label: icon.className,
        }));
    }

    get iconValue() {
        return this.props.record.data[this.props.name] || "";
    }

    get isBottomSheet() {
        return this.env.isSmall && hasTouch();
    }

    getIconTooltip(value) {
        const icon = this.ICONS.find(i => i.className === value);
        return icon?.tooltip || "";
    }

    onSelect(value) {
        this.props.record.update({
            [this.props.name]: value,
        });
    }
}

registry.category("fields").add("fa_icon", {
    component: FontAwesomeIconField,
    supportedTypes: ["char"],
});
