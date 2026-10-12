import { ImageField, imageField } from "@web/views/fields/image/image_field";
import { registry } from "@web/core/registry";
import { computed } from "@odoo/owl";

export class ResourceAvatarField extends ImageField {
    static template = "resource.ResourceAvatarField";

    isUserResource = computed(() => this.props.record.data.resource_type === "user");
    backgroundClass = computed(() => `o_colorlist_item_color_${this.props.record.data.color}`);
}

registry.category("fields").add("resource_avatar", {
    ...imageField,  // includes extractProps, supportedOptions, etc.
    component: ResourceAvatarField,
    fieldDependencies: [
        ...imageField.fieldDependencies,
        { name: "color", type: "integer" },
        { name: "resource_type", type: "selection" },
    ],
});
