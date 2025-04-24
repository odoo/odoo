/** @odoo-module alias=root.widget */

import { createPublicRoot } from "@web/legacy/js/public/public_root";
import lazyloader from "@web/legacy/js/public/lazyloader";
import { WebsiteRoot } from "./website_root";
import { AssetsLoadingError, loadBundle } from "@web/core/assets";

const prom = createPublicRoot(WebsiteRoot).then(async rootInstance => {
    // This data attribute is set by the WebsitePreview client action for a
    // restricted editor user.
    if (window.frameElement) {
        if (window.frameElement.dataset.loadWysiwyg === 'true') {
            try {
                await Promise.all([
                    loadBundle("website.assets_all_wysiwyg"),
                    loadBundle("website.assets_edit_frontend"),
                ]);
            } catch (e) {
                if (e instanceof AssetsLoadingError) {
                    // an AssetsLoadingError caused by a TypeError means that the
                    // fetch request has been cancelled by the browser. It can occur
                    // when the user changes page, or navigate away from the website
                    // client action, so the iframe is unloaded. In this case, we
                    // don't care about reporting the error, it is actually a normal
                    // situation.
                    if (e.cause instanceof TypeError) {
                        return new Promise(() => {});
                    }
                    // "DOMException: The operation was aborted" can occur when unload iframe.
                    // see: https://webidl.spec.whatwg.org/#dom-domexception-abort_err
                    if (e.cause instanceof DOMException && e.cause.name === "AbortError") {
                        return new Promise(() => {});
                    }
                }
                throw e;
            }
        }
        window.dispatchEvent(new CustomEvent('PUBLIC-ROOT-READY', {detail: {rootInstance}}));
    }
    return rootInstance;
});
lazyloader.registerPageReadinessDelay(prom);
export default prom;
