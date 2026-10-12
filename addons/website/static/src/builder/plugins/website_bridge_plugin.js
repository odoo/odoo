import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

/**
 * @typedef { Object } WebsiteBridgeShared
 * @property { WebsiteBridgePlugin['getRegistry'] } getRegistry
 * @property { WebsiteBridgePlugin['getWebsiteContextLang'] } getWebsiteContextLang
 * @property { WebsiteBridgePlugin['getSession'] } getSession
 * @property { WebsiteBridgePlugin['renderToElement'] } renderToElement
 * @property { WebsiteBridgePlugin['renderToFragment'] } renderToFragment
 * @property { WebsiteBridgePlugin['_t'] } _t
 */
export class WebsiteBridgePlugin extends Plugin {
    static id = "websiteBridge";
    static dependencies = [];
    static shared = [
        "getRegistry",
        "getWebsiteContextLang",
        "_t",
        "getSession",
        "renderToElement",
        "renderToFragment",
    ];
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
        // To ensure terms are exported, they must use the `_t` function (avoid renaming)
        return this.getModule("@web/core/l10n/translation")._t;
    }
    getWebsiteContextLang() {
        return {
            lang: this.services.website.currentWebsite.default_lang_id.code,
        };
    }
    getSession() {
        return this.getModule("@web/session").session;
    }
    // For tests with website builder, use `loadIframeBuilderTemplates: true`
    renderToElement(template, context) {
        return this.getModule("@web/core/utils/render").renderToElement(template, context);
    }
    // For tests with website builder, use `loadIframeBuilderTemplates: true`
    renderToFragment(template, context) {
        return this.getModule("@web/core/utils/render").renderToFragment(template, context);
    }
}
registry.category("website-plugins").add(WebsiteBridgePlugin.id, WebsiteBridgePlugin);
registry.category("translation-plugins").add(WebsiteBridgePlugin.id, WebsiteBridgePlugin);
