import { _t } from "@web/core/l10n/translation";
import { ColorList } from "@web/core/colorlist/colorlist";
import { registry } from "@web/core/registry";
import { BadgeTagHexColor } from "@web/core/tags_list/badge_tag_hex_color";
import { Many2ManyTagsField, many2ManyTagsField } from "../many2many_tags/many2many_tags_field";

import { Component, t, useProps } from "@odoo/owl";

/**
 * Hexadecimal codes of the color list entries ($o-colors), so that a tag
 * colored from the list keeps the same color wherever the code is used.
 */
export const COLOR_LIST_HEX_COLORS = [
    "#a2a2a2",
    "#ee2d2d",
    "#dc8534",
    "#e8bb1d",
    "#5794dd",
    "#9f628f",
    "#db8865",
    "#41a9a2",
    "#304be0",
    "#ee2f8a",
    "#61c36e",
    "#9872e6",
];

class Many2ManyTagsHexColorPopover extends Component {
    static template = "web.Many2ManyTagsHexColorPopover";
    static components = { ColorList };
    props = useProps({
        tag: t.object(),
        switchTagColor: t.function(),
        close: t.function(),
    });

    get hexColor() {
        return (this.props.tag.color || "").toLowerCase();
    }

    get selectedColorIndex() {
        const colorIndex = COLOR_LIST_HEX_COLORS.indexOf(this.hexColor);
        return colorIndex > 0 ? colorIndex : undefined;
    }

    get customColor() {
        return /^#[0-9a-f]{6}$/.test(this.hexColor) ? this.hexColor : "#000000";
    }

    onColorSelected(colorIndex) {
        this.props.switchTagColor(COLOR_LIST_HEX_COLORS[colorIndex], this.props.tag);
    }

    onCustomColorChange(ev) {
        this.props.switchTagColor(ev.target.value, this.props.tag);
    }
}

/**
 * Extension of the `many2many_tags` widget in which the color field is a
 * string holding a hexadecimal color code: the tags get the tones of the
 * color list from that code, and editing the color offers the color list
 * along with any custom color.
 */
export class Many2ManyTagsHexColorField extends Many2ManyTagsField {
    static components = {
        ...Many2ManyTagsField.components,
        Tag: BadgeTagHexColor,
        Popover: Many2ManyTagsHexColorPopover,
    };

    getColorPopoverProps(record) {
        return {
            tag: {
                id: record.id,
                color: record.data[this.props.colorField],
            },
            switchTagColor: this.switchTagColor.bind(this),
        };
    }
}

export const many2ManyTagsHexColorField = {
    ...many2ManyTagsField,
    component: Many2ManyTagsHexColorField,
    displayName: _t("Tags with hexadecimal colors"),
    supportedOptions: many2ManyTagsField.supportedOptions.map((option) => {
        if (option.name === "color_field") {
            return {
                ...option,
                availableTypes: ["char"],
                help: _t("Set a char field holding a hexadecimal color to use colors with the tags."),
            };
        }
        return { ...option };
    }),
    additionalClasses: ["o_field_many2many_tags"],
    relatedFields: ({ options }) => {
        const relatedFields = [{ name: "display_name", type: "char" }];
        if (options.color_field) {
            relatedFields.push({ name: options.color_field, type: "char", readonly: false });
        }
        return relatedFields;
    },
};

registry.category("fields").add("many2many_tags_hex_color", many2ManyTagsHexColorField);
