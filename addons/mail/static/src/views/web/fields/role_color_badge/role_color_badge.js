import { useColorPicker } from "@html_editor/components/color_picker/color_picker";
import { getCSSVariableValue, getHtmlStyle } from "@html_editor/utils/formatting";

import { Component, signal, types as t, useProps } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { isCSSColor, normalizeCSSColor } from "@web/core/utils/colors";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

/**
 * Widget for the `res.role` color field.
 *
 * Displays a badge that previews the role's assigned color.
 * Clicking the badge opens a color picker, allowing the user to update the color.
 */
export class RoleColorBadge extends Component {
    static template = "mail.RoleColorBadge";

    props = useProps({ ...standardFieldProps, canBeWrittenTo: t.boolean() });

    colorPickerTrigger = signal.ref();

    setup() {
        useColorPicker(this.colorPickerTrigger, {
            state: {
                selectedColor: this.color,
                defaultTab: "solid",
            },
            applyColor: this.onColorPickerColorClicked.bind(this),
            noTransparency: true,
            useDefaultThemeColors: false,
        });
    }

    /** @returns {string} */
    get style() {
        if (!this.color || !CSS.supports("color", this.color)) {
            return "";
        }
        return `background-color: ${this.color};`;
    }

    /** @returns {string} any CSS color, or "" if unset */
    get color() {
        return this.props.record.data[this.props.name] || "";
    }

    /**
     * @param {string} color either a CSS color (e.g. "#FF0000") or the name of
     * a CSS variable holding one (e.g. "900" for the grayscale buttons).
     */
    onColorPickerColorClicked(color) {
        if (!isCSSColor(color)) {
            color = getCSSVariableValue(color, getHtmlStyle(document));
        }
        if (!isCSSColor(color)) {
            return;
        }
        this.props.record.update({ [this.props.name]: normalizeCSSColor(color) });
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
