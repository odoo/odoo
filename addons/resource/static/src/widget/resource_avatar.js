import { ImageField, imageField } from "@web/views/fields/image/image_field";
import { registry } from "@web/core/registry";

export class ResourceAvatarField extends ImageField {
    static template = "Resource.ResourceAvatarField";

    setup() {
        super.setup();
        const type = this.props.record?.data?.resource_type;
        this.props.isUserResource = type === "user";
        this.props.backgroundClass = `o_colorlist_item_color_${this.props.record.data.color || 0}`;
    }
}

registry.category("fields").add("resource_avatar", {
    ...imageField,  // includes extractProps, supportedOptions, etc.
    component: ResourceAvatarField,
    fieldDependencies: [
        ...imageField.fieldDependencies,
        { name: "resource_type", type: "selection" },
    ],
});
