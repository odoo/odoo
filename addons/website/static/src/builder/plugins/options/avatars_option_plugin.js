import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { ClassAction } from "@html_builder/core/core_builder_action_plugin";
import { BaseOptionComponent } from "@html_builder/core/utils";
import { BorderConfigurator } from "@html_builder/plugins/border_configurator_option";
import { AvatarsHeaderMiddleButtons } from "./avatars_header_buttons";

/**
 * Updates the avatars z-index, depending on the chosen overlapping order.
 *
 * @param {HTMLElement} snippetEl the s_avatars snippet
 */
function updateZIndex(snippetEl) {
    const avatarEls = snippetEl.querySelectorAll(".s_avatars_avatar");
    if (!snippetEl.classList.contains("o_first_on_top")) {
        avatarEls.forEach((avatarEl) => avatarEl.style.removeProperty("z-index"));
        return;
    }
    // Set the avatars `z-index` property to make the first one be on top.
    const totalAvatars = avatarEls.length;
    avatarEls.forEach((avatarEl, index) =>
        avatarEl.style.setProperty("z-index", totalAvatars - index)
    );
}

export class AvatarsOption extends BaseOptionComponent {
    static template = "website.AvatarsOption";
    static selector = ".s_avatars";
    static components = {
        BorderConfigurator,
    };
}

class AvatarsOptionPlugin extends Plugin {
    static id = "avatarsOption";
    static dependencies = ["builderOptions"];

    resources = {
        builder_options: [AvatarsOption],
        builder_header_middle_buttons: {
            Component: AvatarsHeaderMiddleButtons,
            selector: ".s_avatars",
            props: {
                addAvatar: this.addAvatar.bind(this),
                removeAvatar: this.removeAvatar.bind(this),
            },
        },
        builder_actions: {
            AvatarsChangeOrderAction,
        },
        so_content_addition_selector: [".s_avatars"],
    };

    addAvatar(editingElement) {
        const lastAvatarEl = editingElement.querySelector(".o_avatar:last-of-type");
        const newAvatarEl = lastAvatarEl.cloneNode(true);
        lastAvatarEl.after(newAvatarEl);
        updateZIndex(editingElement);
        this.dependencies.builderOptions.setNextTarget(newAvatarEl);
    }

    removeAvatar(editingElement) {
        const lastAvatarEl = editingElement.querySelector(".o_avatar:last-of-type");
        const previousAvatarEl = lastAvatarEl.previousElementSibling;
        lastAvatarEl.remove();
        updateZIndex(editingElement);
        this.dependencies.builderOptions.setNextTarget(previousAvatarEl);
    }
}

export class AvatarsChangeOrderAction extends ClassAction {
    static id = "avatarsChangeOrder";

    apply({ editingElement }) {
        super.apply(...arguments);
        updateZIndex(editingElement);
    }
}

registry.category("website-plugins").add(AvatarsOptionPlugin.id, AvatarsOptionPlugin);
