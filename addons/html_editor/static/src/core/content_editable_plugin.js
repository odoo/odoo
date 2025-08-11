import { isArtificialVoidElement } from "@html_editor/core/selection_plugin";
import { Plugin } from "@html_editor/plugin";
import { selectElements } from "@html_editor/utils/dom_traversal";
import { withSequence } from "@html_editor/utils/resource";

/**
 * This plugin is responsible for setting the contenteditable attribute on some
 * elements.
 *
 * The force_editable_selector and force_not_editable_selector resources allow
 * other plugins to easily add editable or non editable elements.
 */

export class ContentEditablePlugin extends Plugin {
    static id = "contentEditablePlugin";
    resources = {
        normalize_handlers: withSequence(5, this.normalize.bind(this)),
        clean_for_save_handlers: withSequence(Infinity, this.cleanForSave.bind(this)),
        system_classes: ["o_editable_media"],
    };

    normalize(root) {
        const toDisableSelector = this.getResource("force_not_editable_selector").join(",");
        const toDisableEls = toDisableSelector ? [...selectElements(root, toDisableSelector)] : [];
        for (const toDisable of toDisableEls) {
            toDisable.setAttribute("contenteditable", "false");
        }
        const toEnableSelector = this.getResource("force_editable_selector").join(",");
        let filteredContentEditableEls = toEnableSelector
            ? [...selectElements(root, toEnableSelector)]
            : [];
        for (const fn of this.getResource("filter_contenteditable_handlers")) {
            filteredContentEditableEls = [...fn(filteredContentEditableEls)];
        }
        const extraContentEditableEls = [];
        for (const fn of this.getResource("extra_contenteditable_handlers")) {
            extraContentEditableEls.push(...fn(filteredContentEditableEls));
        }
        for (const contentEditableEl of [
            ...filteredContentEditableEls,
            ...extraContentEditableEls,
        ]) {
            if (!contentEditableEl.isContentEditable) {
                if (
                    isArtificialVoidElement(contentEditableEl) ||
                    contentEditableEl.nodeName === "IMG"
                ) {
                    contentEditableEl.classList.add("o_editable_media");
                    continue;
                }
                if (!contentEditableEl.matches(toDisableSelector)) {
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
