/** @odoo-module alias=root.widget */

import { createPublicRoot } from "@web/legacy/js/public/public_root";
import { WebsiteRoot } from "./website_root";
import { loadLegacyWysiwygAssets } from "@web_editor/js/frontend/loader";

export default createPublicRoot(WebsiteRoot).then(rootInstance => {
    // This data attribute is set by the WebsitePreview client action for a
    // restricted editor user.
    if (window.frameElement && window.frameElement.dataset.loadWysiwyg === 'true') {
        loadLegacyWysiwygAssets(['web_editor.assets_wysiwyg', 'website.assets_wysiwyg']).then(() => {
            window.dispatchEvent(new CustomEvent('PUBLIC-ROOT-READY', {detail: {rootInstance}}));
        });
    }
    return rootInstance;
});
