/** @odoo-module alias=root.widget */

import { createPublicRoot } from "@web/legacy/js/public/public_root";
import { registerPageReadinessDelay } from "@web/public/lazyloader";
import { WebsiteRoot } from "./website_root";

const prom = createPublicRoot(WebsiteRoot).then(async (rootInstance) => {
    if (window.frameElement) {
        window.dispatchEvent(new CustomEvent("PUBLIC-ROOT-READY", { detail: { rootInstance } }));
    }
    return rootInstance;
});
registerPageReadinessDelay(prom);
export default prom;
