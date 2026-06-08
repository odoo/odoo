import { props, t } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { SlideCategoryListRenderer } from "./slide_category_list_renderer";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";

class SlideCategoryOneToManyField extends X2ManyField {
    static components = {
        ...X2ManyField.components,
        ListRenderer: SlideCategoryListRenderer,
    };
    props = props({
        // Inlined from X2ManyField, which is not yet converted to the owl3
        // props schema.
        ...standardFieldProps,
        addLabel: t.string().optional(),
        editable: t.string().optional("bottom"),
        viewMode: t.string().optional(),
        widget: t.string().optional(),
        crudOptions: t.object().optional(),
        string: t.string().optional(),
        relatedFields: t.object().optional(),
        views: t.object().optional(),
        domain: t.or([t.array(), t.function()]).optional(),
        context: t.object(),
    });
    setup() {
        super.setup();
        this.canOpenRecord = true;
    }
}

registry.category("fields").add("slide_category_one2many", {
    ...x2ManyField,
    relatedFields: [{ name: "is_category", type: "boolean", readonly: false }],
    component: SlideCategoryOneToManyField,
    additionalClasses: [...(x2ManyField.additionalClasses || []), "o_field_one2many"],
});
