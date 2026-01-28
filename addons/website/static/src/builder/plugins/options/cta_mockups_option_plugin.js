import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class CTAMockupsOptionPlugin extends Plugin {
    static id = "ctaMockupsOptions";
    resources = {
        on_snippet_dropped_handlers: this.onSnippetDropped.bind(this),
    };

    // Todo: Remove this logic before merging into the master branch.
    onSnippetDropped({ snippetEl }) {
        if (snippetEl.classList.contains("s_cta_mockups")) {
            const imgEls = snippetEl.querySelectorAll("img");
            // As XML changes are not allowed in stable version, the shape
            // colors are initialised here.
            const shapeColors = [";;#F3F2F2;;", ";;;;#111827"];
            imgEls.forEach((imgEl, index) => {
                imgEl.setAttribute("data-shape-colors", shapeColors[index]);
            });
        }
    }
}
registry.category("website-plugins").add(CTAMockupsOptionPlugin.id, CTAMockupsOptionPlugin);
