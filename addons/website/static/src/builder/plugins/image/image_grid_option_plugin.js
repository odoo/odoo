import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { ImageGridOption } from "./image_grid_option";
import { withSequence } from "@html_editor/utils/resource";
import { GRID_IMAGE } from "@website/builder/option_sequence";
import { BuilderAction } from "@html_builder/core/builder_action";

class ImageGridOptionPlugin extends Plugin {
    static id = "imageGridOption";

    resources = {
        builder_options: [
            withSequence(GRID_IMAGE, {
                OptionComponent: ImageGridOption,
                selector: "img",
            }),
        ],
        builder_actions: {
            SetGridImageModeAction,
        },
    };
}

export class SetGridImageModeAction extends BuilderAction {
    static id = "setGridImageMode";
    isApplied({ editingElement, value: modeName }) {
        const imageGridItemEl = editingElement.closest(".o_grid_item_image");
        const withContain = imageGridItemEl.classList.contains("o_grid_item_image_contain");

        return withContain ? modeName === "contain" : modeName === "cover";
    }
    apply({ editingElement, value: modeName }) {
        const imageGridItemEl = editingElement.closest(".o_grid_item_image");
        if (modeName === "contain") {
            imageGridItemEl.classList.add("o_grid_item_image_contain");
        } else if (modeName === "cover") {
            imageGridItemEl.classList.remove("o_grid_item_image_contain");
        }
    }
}

registry.category("website-plugins").add(ImageGridOptionPlugin.id, ImageGridOptionPlugin);
