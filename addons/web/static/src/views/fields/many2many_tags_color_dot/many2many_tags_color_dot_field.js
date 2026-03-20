import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { Many2ManyTagsField, many2ManyTagsField } from "../many2many_tags/many2many_tags_field";
import { BadgeTagDot } from "@web/core/tags_list/badge_tag_dot";

/**
 * Extension of the `many2many_tags` widget in which the color field is a
 * string accepting a hexadecimal color code.
 *
 * Instead of coloring the entire tag background (default behavior), this widget
 * displays a colored bullet (dot) placed before the tag label. This allows the
 * tag to keep its regular appearance while visually indicating its color
 * through the small dot.
 */
class Many2ManyTagsColorDotField extends Many2ManyTagsField {
    static components = {
        ...Many2ManyTagsField.components,
        Tag: BadgeTagDot,
    };
}

const supportedOptions = many2ManyTagsField.supportedOptions
    .filter((option) => option.name !== "on_tag_click")
    .map((option) => {
        if (option.name === "color_field") {
            return {
                ...option,
                label: _t("Dot color field"),
                help: _t("Set a char field that colors the dot on the tag."),
                availableTypes: ["char"],
            };
        }
        return { ...option };
    });
supportedOptions.push({
    name: "can_open",
    label: _t("Open form on tag click"),
    type: "boolean",
});

export const many2ManyTagsColorDotField = {
    ...many2ManyTagsField,
    component: Many2ManyTagsColorDotField,
    displayName: _t("Color dot tags"),
    supportedOptions,
    supportedTypes: ["many2many"],
    additionalClasses: ["o_field_many2many_tags"],
    relatedFields: ({ options }) => {
        const relatedFields = [{ name: "display_name", type: "char" }];
        if (options.color_field) {
            relatedFields.push({ name: options.color_field, type: "char", readonly: false });
        }
        return relatedFields;
    },
    extractProps({ attrs, options, string, placeholder }, dynamicInfo) {
        const props = many2ManyTagsField.extractProps(
            { attrs, options, string, placeholder },
            dynamicInfo
        );
        delete props.onTagClick;
        if (options.can_open) {
            props.onTagClick = "open_form";
        }
        return props;
    },
};

registry.category("fields").add("many2many_tags_color_dot", many2ManyTagsColorDotField);
