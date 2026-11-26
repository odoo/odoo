import { Component, computed, useProps } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { CharField } from "@web/views/fields/char/char_field";
import { FieldSelectorField } from "@web/views/fields/field_selector/field_selector_field";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { DynamicSelectionField } from "@web_tutorial/dynamic_selection_field/dynamic_selection_field";

/** The types of steps naming one of the options computed by the server */
const SELECTION_TYPES = ["generic_button", "menu_item", "server_action"];

/**
 * The name of a tutorial step, depending on its type: a field of the model of
 * its views, picked in its fields (or in the ones of the lines of a x2many
 * field, the only relations followed); a method, typed in; a generic button,
 * a server action or a menu, picked among the options computed by the server
 * (see `name_selection_options`); none for a dialog
 */
export class TutorialStepNameField extends Component {
    static components = { CharField, DynamicSelectionField, FieldSelectorField };
    static template = "web_tutorial.TutorialStepNameField";

    props = useProps(standardFieldProps);
    selectorProps = computed(() => ({
        ...this.props,
        followRelation: ({ fieldDef }) => ["one2many", "many2many"].includes(fieldDef.type),
        model: "res_model",
    }));
    isSelection = computed(() => SELECTION_TYPES.includes(this.type()));
    type = computed(() => this.props.record.data.type);
}

registry.category("fields").add("tutorial_step_name", {
    component: TutorialStepNameField,
    fieldDependencies: [
        { name: "name_selection_options", type: "json" },
        { name: "res_model", type: "char" },
        { name: "type", type: "selection" },
    ],
    supportedTypes: ["char"],
});
