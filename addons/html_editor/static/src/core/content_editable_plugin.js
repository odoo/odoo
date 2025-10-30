import { isArtificialVoidElement } from "@html_editor/core/selection_plugin";
import { Plugin } from "@html_editor/plugin";
import { selectElements } from "@html_editor/utils/dom_traversal";
import { withSequence } from "@html_editor/utils/resource";

/**
 * This plugin is responsible for setting the contenteditable attribute on some
 * elements.
 *
 * The content_editable_providers and content_not_editable_providers resources
 * allow other plugins to easily add editable or non editable elements.
 */

export class ContentEditablePlugin extends Plugin {
    static id = "contentEditablePlugin";
    resources = {
        normalize_handlers: withSequence(5, this.normalize.bind(this)),
        clean_for_save_handlers: withSequence(Infinity, this.cleanForSave.bind(this)),
    };

    normalize(root) {
        const contentNotEditableEls = [];
        for (const fn of this.getResource("content_not_editable_providers")) {
            contentNotEditableEls.push(...fn(root));
        }
        for (const contentNotEditableEl of contentNotEditableEls) {
            contentNotEditableEl.setAttribute("contenteditable", "false");
        }
        const contentEditableEls = [];
        for (const fn of this.getResource("content_editable_providers")) {
            contentEditableEls.push(...fn(root));
        }
        const filteredContentEditableEls = contentEditableEls.filter((contentEditableEl) =>
            this.getResource("valid_contenteditable_predicates").every((p) => p(contentEditableEl))
        );
        for (const contentEditableEl of filteredContentEditableEls) {
            if (!contentEditableEl.isContentEditable) {
                if (
                    isArtificialVoidElement(contentEditableEl) ||
                    contentEditableEl.nodeName === "IMG"
                ) {
                    contentEditableEl.classList.add("o_editable_media");
                    continue;
                }
                if (!contentNotEditableEls.includes(contentEditableEl)) {
                    contentEditableEl.setAttribute("contenteditable", true);
                }
            }
        }
    }

    cleanForSave({ root }) {
        const toRemoveSelector = this.getResource("contenteditable_to_remove_selector").join(",");
        const contenteditableEls = toRemoveSelector
            ? [...selectElements(root, toRemoveSelector)]
            : [];
        for (const contenteditableEl of contenteditableEls) {
            contenteditableEl.removeAttribute("contenteditable");
        }
    }
}
