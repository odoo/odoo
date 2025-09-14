import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { BuilderAction } from "@html_builder/core/builder_action";
import { renderToElement } from "@web/core/utils/render";
import { useDomState } from "@html_builder/core/utils";
import { useOperation } from "@html_builder/core/operation_plugin";
import { Component } from "@odoo/owl";

class AvatarsHeaderMiddleButtons extends Component {
    static template = "website.AvatarsHeaderMiddleButtons";
    static props = {
        addAvatar: Function,
        removeAvatar: Function,
    };

    setup() {
        this.state = useDomState((editingElement) => {
            const containerEl = editingElement.querySelector('.s_avatars_rules_collector');
            return {
                avatarEls: containerEl ? containerEl.querySelectorAll('.o_avatar') : [],
            };
        });

        this.callOperation = useOperation();
    }

    addAvatar() {
        this.callOperation(async () => {
            await this.props.addAvatar(this.env.getEditingElement());
        });
    }

    removeAvatar() {
        this.callOperation(() => {
            this.props.removeAvatar(this.env.getEditingElement());
        });
    }
}

class AvatarsOptionPlugin extends Plugin {
    static id = "avatarsOption";

    resources = {
        builder_options: [
            {
                template: "website.AvatarsOption",
                selector: ".s_avatars",
            },
        ],
        builder_header_middle_buttons: {
            Component: AvatarsHeaderMiddleButtons,
            selector: ".s_avatars",
            props: {
                addAvatar: async (editingElement) => await this.addAvatar(editingElement),
                removeAvatar: (editingElement) => this.removeAvatar(editingElement),
            },
        },
        builder_actions: {
            AvatarsAddContentAction,
        },
        so_content_addition_selector: [".s_avatars"],
    };

    async addAvatar(editingElement) {
        const newAvatarIndex = editingElement.querySelectorAll('.o_avatar').length + 1;
        const picIndex = Math.min(newAvatarIndex, 6);
        const newAvatarEl = renderToElement("website.s_avatars.avatar", { picIndex });
        const containerEl = editingElement.querySelector('.s_avatars_rules_collector');
        containerEl.append(newAvatarEl);
    }

    removeAvatar(editingElement) {
        const lastAvatarEl = editingElement.querySelector('.o_avatar:last-of-type');
        lastAvatarEl.remove();
    }
}

class AvatarsAddContentAction extends BuilderAction {
    static id = "avatarsAddContent";
    static dependencies = ["builderOptions"];

    isApplied({ editingElement, params }) {
        return !!editingElement.querySelector(params.elSelector);
    }

    apply({ editingElement, isPreviewing, params }) {
        if (isPreviewing) {
            return;
        }

        const existingElement = editingElement.querySelector(params.elSelector);
        if (existingElement) {
            existingElement.remove();
        } else {
            const elToAdd = renderToElement(params.elView);
            const parentEl = editingElement.querySelector(params.elParent) || editingElement;
            parentEl.append(elToAdd);
        }
    }
}

registry.category("website-plugins").add(AvatarsOptionPlugin.id, AvatarsOptionPlugin);
