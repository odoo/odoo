import { Plugin } from "@html_editor/plugin";

export class SnippetNamePlugin extends Plugin {
    static id = "snippetName";
    /** @type {import("plugins").BuilderResources} */
    resources = {
        clean_for_save_processors: (rootEl) => {
            for (const el of rootEl.querySelectorAll("[data-dynamic-builder-name]")) {
                console.warn(
                    `data-dynamic-builder-name should only be set dynamically by the template, and not saved in view (found ${el.dataset.dynamicBuilderName})`
                );
                el.removeAttribute("data-dynamic-builder-name");
            }
            return rootEl;
        },
    };
}
