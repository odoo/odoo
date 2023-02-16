/** @odoo-module */

import { SectionListRenderer } from "./section_list_renderer";
import { registry } from "@web/core/registry";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";

class SectionOneToManyField extends X2ManyField {}
SectionOneToManyField.components = {
    ...X2ManyField.components,
    ListRenderer: SectionListRenderer,
};
SectionOneToManyField.defaultProps = {
    ...X2ManyField.defaultProps,
    editable: "bottom",
};

registry.category("fields").add("section_one2many", {
    ...x2ManyField,
    component: SectionOneToManyField,
});
