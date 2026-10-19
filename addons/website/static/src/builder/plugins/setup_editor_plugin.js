import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class WebsiteSetupEditorPlugin extends Plugin {
    static id = "website.setup_editor_plugin";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        snippet_preview_dialog_bundles: ["web.assets_frontend"],
        snippet_preview_dialog_stylesheets_processors: (params) => {
            const fontLinkEls = this.document.head.querySelectorAll(
                'link[rel="stylesheet"][href^="https://fonts.googleapis.com/css"], ' +
                    'link[rel="stylesheet"][href*="/google-font-"]'
            );
            for (const fontLinkEl of fontLinkEls) {
                params.iframe.contentDocument.head.appendChild(fontLinkEl.cloneNode(true));
            }
            return params;
        },
    };
}

registry.category("website-plugins").add(WebsiteSetupEditorPlugin.id, WebsiteSetupEditorPlugin);
registry.category("translation-plugins").add(WebsiteSetupEditorPlugin.id, WebsiteSetupEditorPlugin);
