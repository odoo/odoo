import { Component, computed, t, useProps } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { SelectMenu } from "@web/core/select_menu/select_menu";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

/**
 * A char field picked among the options of a json field of its record, as
 * (value, label) pairs computed by the server; several values being stored
 * separated by commas
 */
export class DynamicSelectionField extends Component {
    static components = { SelectMenu };
    static template = "web_tutorial.DynamicSelectionField";

    props = useProps({
        ...standardFieldProps,
        multiSelect: t.boolean().optional(false),
        optionsField: t.string(),
        placeholder: t.string().optional(),
    });
    choices = computed(() =>
        (this.props.record.data[this.props.optionsField] || []).map(([value, label]) => ({
            value,
            label,
        }))
    );
    values = computed(() => {
        const value = this.props.record.data[this.props.name] || "";
        return (this.props.multiSelect ? value.split(",") : [value])
            .map((part) => part.trim())
            .filter(Boolean);
    });
    value = computed(() => (this.props.multiSelect ? this.values() : this.values()[0] || false));
    labels = computed(() =>
        this.values().map(
            (value) => this.choices().find((choice) => choice.value === value)?.label || value
        )
    );

    /**
     * @param {string|string[]} value
     */
    onSelect(value) {
        this.props.record.update({
            [this.props.name]: this.props.multiSelect ? value.join(",") : value,
        });
    }
}

registry.category("fields").add("tutorial_dynamic_selection", {
    component: DynamicSelectionField,
    extractProps: ({ options, placeholder }) => ({
        multiSelect: Boolean(options.multi_select),
        optionsField: options.options_field,
        placeholder,
    }),
    fieldDependencies: ({ options }) => [{ name: options.options_field, type: "json" }],
    supportedTypes: ["char"],
});
