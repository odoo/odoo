import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

/**
 * On /website/demo/snippets,some snippets calling sub-templates are not,
 * branded so their options cannot be shown. Make `#wrap` savable so they can
 * be selected.
 */
export class SnippetsDebugPagePlugin extends Plugin {
    static id = "snippetsDebugPage";

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        savable_selectors: "#wrap.o_snippets_debug_page",
    };
}

registry.category("website-plugins").add(SnippetsDebugPagePlugin.id, SnippetsDebugPagePlugin);
