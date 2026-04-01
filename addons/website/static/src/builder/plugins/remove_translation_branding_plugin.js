import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class RemoveTranslationBrandingPlugin extends Plugin {
    static id = "removeTranslationBrandingPlugin";

    setup() {
        // Cleaning translation branding nodes that could have been saved
        // by error between with code between d4d428ff1d (29th October 2025) and
        // f09dc4d9d3 (19th November 2025)
        this.editable
            .querySelectorAll("span[data-oe-model][data-oe-translation-source-sha]")
            .forEach((brandingElement) => {
                brandingElement.replaceWith(...brandingElement.childNodes);
            });
    }
}

registry
    .category("website-plugins")
    .add(RemoveTranslationBrandingPlugin.id, RemoveTranslationBrandingPlugin);
