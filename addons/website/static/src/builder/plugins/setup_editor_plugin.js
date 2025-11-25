import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class WebsiteSetupEditorPlugin extends Plugin {
    static id = "website.setup_editor_plugin";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        snippet_preview_dialog_bundles: ["web.assets_frontend"],
    };
}

registry.category("website-plugins").add(WebsiteSetupEditorPlugin.id, WebsiteSetupEditorPlugin);
