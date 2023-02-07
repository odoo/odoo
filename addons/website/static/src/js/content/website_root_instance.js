/** @odoo-module alias=root.widget */

import { createPublicRoot } from "@web/legacy/js/public/public_root";
import { WebsiteRoot } from "./website_root";
import { getBundle, loadBundle } from "@web/core/assets";

export default createPublicRoot(WebsiteRoot).then(async (rootInstance) => {
    // This data attribute is set by the WebsitePreview client action for a
    // restricted editor user.
    if (window.frameElement && window.frameElement.dataset.loadWysiwyg === 'true') {
        const assets = await getBundle("website.assets_all_wysiwyg");
        await loadBundle(assets);
        window.dispatchEvent(new CustomEvent('PUBLIC-ROOT-READY', {detail: {rootInstance}}));
    }
    return rootInstance;
});
