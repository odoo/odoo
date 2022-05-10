/** @odoo-module alias=root.widget */

import { createPublicRoot } from "@web/legacy/js/public/public_root";
import { WebsiteRoot } from "./website_root";
import { loadWysiwyg } from "web_editor.loader";

export default createPublicRoot(WebsiteRoot).then(rootInstance => {
    if (window.parent !== window) {
        loadWysiwyg(['website.compiled_assets_wysiwyg']).then(() => {
            window.dispatchEvent(new CustomEvent('PUBLIC-ROOT-READY', {detail: {rootInstance}}));
        });
    }
    return rootInstance;
});
