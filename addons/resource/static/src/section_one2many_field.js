import { SectionListRenderer } from "./section_list_renderer";
import { registry } from "@web/core/registry";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";

class SectionOneToManyField extends X2ManyField {
    static components = {
        ...X2ManyField.components,
        ListRenderer: SectionListRenderer,
    };
    static defaultProps = {
        ...X2ManyField.defaultProps,
        editable: "bottom",
    };
}

registry.category("fields").add("section_one2many", {
    ...x2ManyField,
    component: SectionOneToManyField,
    additionalClasses: [...x2ManyField.additionalClasses || [], "o_field_one2many"],
});
