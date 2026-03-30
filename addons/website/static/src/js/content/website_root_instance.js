/** @odoo-module alias=root.widget */

import { createPublicRoot } from "@web/legacy/js/public/public_root";
import lazyloader from "web.public.lazyloader";
import { WebsiteRoot } from "./website_root";
import { loadWysiwyg } from "web_editor.loader";

const prom = createPublicRoot(WebsiteRoot).then(rootInstance => {
    // This data attribute is set by the WebsitePreview client action for a
    // restricted editor user.
    if (window.frameElement) {
        let prepare = Promise.resolve();
        if (window.frameElement.dataset.loadWysiwyg === 'true') {
            prepare = loadWysiwyg(['website.assets_wysiwyg_inside']);
        }
        prepare.then(() => {
            window.dispatchEvent(new CustomEvent('PUBLIC-ROOT-READY', {detail: {rootInstance}}));
        });
    }
    return rootInstance;
});
lazyloader.registerPageReadinessDelay(prom);
export default prom;
