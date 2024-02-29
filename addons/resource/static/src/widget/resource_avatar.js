import { CharField } from "@web/views/fields/char/char_field";
import { registry } from "@web/core/registry";

export class nameWithAvatarWidget extends CharField {
    static template = "resource.ResourceAvatar";
}

const nameWithAvatar = {
    ...CharField,
    component:nameWithAvatarWidget,
    fieldDependencies: [{ name: "resource_type", type: "selection" }],
};

registry.category("fields").add("resource_avatar", nameWithAvatar);
