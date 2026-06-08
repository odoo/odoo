import { registry } from "@web/core/registry";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";

import { DependOnIdsListRenderer } from "./depend_on_ids_list_renderer";

export class DependOnIdsOne2ManyField extends X2ManyField {
    static components = {
        ...X2ManyField.components,
        ListRenderer: DependOnIdsListRenderer,
    };
}

export const dependOnIdsOne2ManyField = {
    ...x2ManyField,
    component: DependOnIdsOne2ManyField,
};

registry.category("fields").add("depend_on_ids_one2many", dependOnIdsOne2ManyField);
