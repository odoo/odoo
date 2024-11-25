import { registry } from "@web/core/registry";
import {
    Many2ManyTagsField,
    many2ManyTagsField,
} from "@web/views/fields/many2many_tags/many2many_tags_field";

export class Many2ManyPlaceholderListView extends Many2ManyTagsField {
    static template = "point_of_sale.Many2ManyPlaceholderListView";
}

export const many2ManyPlaceholderListView = {
    ...many2ManyTagsField,
    component: Many2ManyPlaceholderListView,
    additionalClasses: ["o_field_many2many_tags"],
};

registry
    .category("fields")
    .add("many2many_tags_placeholder_list_view", many2ManyPlaceholderListView);
