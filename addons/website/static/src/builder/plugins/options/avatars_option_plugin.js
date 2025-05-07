import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { BuilderAction } from "@html_builder/core/builder_action";
import { renderToElement } from "@web/core/utils/render";

class AvatarsOptionPlugin extends Plugin {
    static id = "avatarsOption";

    resources = {
        builder_options: [
            {
                template: "website.AvatarsOption",
                selector: ".s_avatars",
            },
        ],
        builder_actions: {
            AvatarsAddContentAction,
        },
        so_content_addition_selector: [".s_avatars"],
    };
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
