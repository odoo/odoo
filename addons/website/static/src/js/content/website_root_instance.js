/** @odoo-module alias=root.widget */

import { createPublicRoot } from "@web/legacy/js/public/public_root";
import { WebsiteRoot } from "./website_root";
import { getBundle, loadCSS, loadJS } from "@web/core/assets";

export default createPublicRoot(WebsiteRoot).then(async (rootInstance) => {
    // This data attribute is set by the WebsitePreview client action for a
    // restricted editor user.
    if (window.frameElement && window.frameElement.dataset.loadWysiwyg === 'true') {
        await Promise.all([
            getBundle('web_editor.assets_wysiwyg_light').then(bundle => bundle.jsLibs.map(loadJS)),
            getBundle("web_editor.assets_wysiwyg").then(bundle => bundle.cssLibs.map(loadCSS)),
            getBundle("website.assets_wysiwyg").then(bundle => bundle.cssLibs.map(loadCSS)),
        ]);

        window.dispatchEvent(new CustomEvent('PUBLIC-ROOT-READY', {detail: {rootInstance}}));
    }
    return rootInstance;
});
