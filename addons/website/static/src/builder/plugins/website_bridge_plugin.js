import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class WebsiteBridgePlugin extends Plugin {
    static id = "websiteBridge";
    static dependencies = [];
    static shared = ["getRegistry", "getWebsiteContextLang", "_t"];
    ensureModuleLoader() {
        if (!this.moduleLoader) {
            this.moduleLoader = this.window.odoo.loader;
        }
    }
    getModule(moduleName) {
        this.ensureModuleLoader();
        return this.moduleLoader.require(moduleName);
    }
    getRegistry() {
        return this.getModule("@web/core/registry").registry;
    }
    get _t() {
        return this.getModule("@web/core/l10n/translation")._t;
    }
    getWebsiteContextLang() {
        return {
            lang: this.services.website.currentWebsite.default_lang_id.code,
        };
    }
}
registry.category("website-plugins").add(WebsiteBridgePlugin.id, WebsiteBridgePlugin);
