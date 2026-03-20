import { Plugin } from "@html_editor/plugin";
import { selectElements } from "@html_editor/utils/dom_traversal";
import { withSequence } from "@html_editor/utils/resource";
import { unwrapContents } from "@html_editor/utils/dom";

/**
 * @typedef {import("plugins").CSSSelector[]} force_background_translation_state_selectors
 * elements that may be inside a translation span and have a background-color
 * hiding the span's color showing the translation state
 */

export class RepeatTranslationStatePlugin extends Plugin {
    static id = "translateStateInButton";
    static dependencies = ["selection"];

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        // lower sequence than the default to run before FeffPlugin's handler
        normalize_handlers: withSequence(5, (root) => {
            const cursors = this.dependencies.selection.preserveSelection();
            for (const el of root.querySelectorAll(".o_translation_state_inner_span")) {
                unwrapContents(el);
            }
            for (const el of selectElements(
                root,
                `[data-oe-translation-state] :is(${this.getResource(
                    "force_background_translation_state_selectors"
                ).join(",")})`
            )) {
                // wrap content in span.o_translation_state_inner_span
                const repeater = this.document.createElement("span");
                repeater.classList.add("o_translation_state_inner_span");
                repeater.replaceChildren(...el.childNodes);
                el.replaceChildren(repeater);
            }
            cursors.restore();
        }),
        clean_for_save_handlers: ({ root }) => {
            for (const el of selectElements(root, ".o_translation_state_inner_span")) {
                unwrapContents(el);
            }
        },
    };
}
