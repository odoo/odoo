import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { withSequence } from "@html_editor/utils/resource";
import { BuilderAction } from "@html_builder/core/builder_action";
import { REPLACE_MEDIA } from "@html_builder/utils/option_sequence";
import { ReplaceMediaOption } from "./replace_media_option";

export const REPLACE_MEDIA_SELECTOR =
    "img, .media_iframe_video, span.fa, i.fa, .o_file_box";
export const REPLACE_MEDIA_EXCLUDE =
    "[data-oe-xpath], a[href^='/website/social/'] > i.fa, a[class*='s_share_'] > i.fa";

export class ReplaceMediaOptionPlugin extends Plugin {
    static id = "replaceMediaOption";
    static dependencies = [
        "history",
    ];
    resources = {
        builder_options: [
            withSequence(REPLACE_MEDIA, {
                OptionComponent: ReplaceMediaOption,
                selector: REPLACE_MEDIA_SELECTOR,
                exclude: REPLACE_MEDIA_EXCLUDE,
                name: "replaceMediaOption",
            }),
        ],
        builder_actions: {
            ReplaceMediaAction,
        },
        on_media_dialog_saved_handlers: async (elements, { node }) => {
            this.cleanupEmptyMediaClasses(elements[0]);
        },
    };

    /**
     * Removes specific classes from an element if no matching content exists inside.
     * @param {Element} element - The DOM element to clean up.
     * @param {Array<[string, string]>} rules - Array of [className, selector] pairs.
     */
    cleanupEmptyMediaClasses(element, rules = [
        ["o_image", "img"],
        ["o_file_box", ".o_file_image"],
        ["s_video", "iframe"],
    ]) {
        rules.forEach(([cls, selector]) => {
            if (element.classList.contains(cls) && !element.querySelector(selector)) {
                element.classList.remove(cls);
            }
        });
    }

}

class ReplaceMediaAction extends BuilderAction {
    static id = "replaceMedia";
    static dependencies = ["media", "history", "builderOptions"];
    async load({ editingElement }) {
        let media;
        let activeTab = editingElement.classList.contains("o_file_box")
            ? "DOCUMENTS"
            : undefined;
        await this.dependencies.media.openMediaDialog({
            activeTab: activeTab,
            node: editingElement,
            save: (newMedia) => {
                media = newMedia;
            },
        });
        return media;
    }
    apply({ editingElement, loadResult: newMedia }) {
        if (!newMedia) {
            return;
        }
        const parent = editingElement.parentNode;
        if (parent) {
            parent.insertBefore(newMedia, editingElement);
            parent.removeChild(editingElement);
        }
        this.dependencies.history.addStep();
        this.dependencies["builderOptions"].updateContainers(newMedia);
    }
}

registry.category("website-plugins").add(ReplaceMediaOptionPlugin.id, ReplaceMediaOptionPlugin);
