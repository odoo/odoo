import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { renderToElement } from "@web/core/utils/render";
import { AvatarsHeaderMiddleButtons } from "./avatars_header_buttons";

class AvatarsHeaderOptionPlugin extends Plugin {
    static id = "avatarsTopOption";
    static dependencies = ["clone"];
    resources = {
        builder_header_middle_buttons: {
            Component: AvatarsHeaderMiddleButtons,
            selector: ".s_avatars",
            props: {
                addAvatar: async (editingElement) => await this.addAvatar(editingElement),
                removeAvatar: (editingElement) => this.removeAvatar(editingElement),
            },
        },
    };

    async addAvatar(editingElement) {
        const newAvatarIndex = editingElement.querySelectorAll('.o_avatar').length + 1;
        const picIndex = Math.min(newAvatarIndex, 6);
        const newAvatarEl = renderToElement("website.s_avatars.avatar", { picIndex });
        const containerEl = editingElement.querySelector('.s_avatars_rules_collector');
        if (containerEl) {
            containerEl.append(newAvatarEl);
        }
    }

    removeAvatar(editingElement) {
        const lastAvatarEl = editingElement.querySelector('.o_avatar:last-of-type');
        if (lastAvatarEl) {
            lastAvatarEl.remove();
        }
    }
}
registry.category("website-plugins").add(AvatarsHeaderOptionPlugin.id, AvatarsHeaderOptionPlugin);
