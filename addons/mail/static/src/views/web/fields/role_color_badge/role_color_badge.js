import { useColorPicker } from "@html_editor/components/color_picker/color_picker";

import { Component, props, types as t } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

/**
 * Hexadecimal representation of an RGB color.
 * It consists of a '#' followed by 6 hexadecimal digits.
 * @typedef {`#${string}`} HexCode
 */

/**
 * Widget for the `res.role` color field.
 *
 * Displays a badge that previews the role's assigned color.
 * Clicking the badge opens a color picker, allowing the user to update the color.
 */
export class RoleColorBadge extends Component {
    static template = "mail.RoleColorBadge";

    props = props({ ...standardFieldProps, canBeWrittenTo: t.boolean() });

    setup() {
        useColorPicker("colorPickerTrigger", {
            state: {
                selectedColor: this.hexCode,
                defaultTab: "solid",
            },
            applyColor: this.onColorPickerColorClicked.bind(this),
            noTransparency: true,
            useDefaultThemeColors: false,
        });
    }

    /** @returns {string} */
    get style() {
        if (!/^#[A-F0-9]{6}$/i.test(this.hexCode)) {
            return "";
        }
        return `background-color: ${this.hexCode};`;
    }

    /** @returns {HexCode | ""} */
    get hexCode() {
        return this.props.record.data[this.props.name] || "";
    }

    /** @param {HexCode} hexCode */
    onColorPickerColorClicked(hexCode) {
        this.props.record.update({ [this.props.name]: hexCode });
    }
}

registry.category("fields").add("mail_role_color_badge", {
    component: RoleColorBadge,
    displayName: _t("Role Color Badge"),
    supportedTypes: ["char"],
    /**
     * In `extractProps`, `readonly` simply indicates whether the user can write
     * to the field (based on access rights and read-only status). We store this
     * info in `canBeWrittenTo` because the final `readonly` value also accounts
     * for whether the view is currently in edit mode. This ensures that
     * clicking the badge opens the color picker if the user has sufficient
     * rights, regardless of the view's current mode.
     */
    extractProps: (_fieldInfo, { readonly }) => ({ canBeWrittenTo: !readonly }),
});
