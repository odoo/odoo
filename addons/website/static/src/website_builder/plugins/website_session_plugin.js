import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class WebsiteSessionPlugin extends Plugin {
    static id = "websiteSession";
    static shared = ["getSession"];

    getSession() {
        return this.window.odoo.loader.modules.get("@web/session").session;
    }
}

registry.category("website-plugins").add(WebsiteSessionPlugin.id, WebsiteSessionPlugin);
