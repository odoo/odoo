/** @odoo-module alias=root.widget */

import { createPublicRoot } from "@web/legacy/js/public/public_root";
import lazyloader from "@web/legacy/js/public/lazyloader";
import { WebsiteRoot } from "./website_root";
import { AssetsLoadingError, loadBundle, loadCSS, loadJS } from "@web/core/assets";

const prom = createPublicRoot(WebsiteRoot).then(async rootInstance => {
    // This data attribute is set by the WebsitePreview client action for a
    // restricted editor user.
    if (window.frameElement) {
        if (window.frameElement.dataset.loadWysiwyg === 'true') {
            // `getBundle` fetches the URL of the bundle by including
            // `session.bundle_params` as search params. The `lang` search param
            // in particular determines if the CSS bundles are fetch in their
            // RTL version or not. 
            // For `website.assets_all_wysiwyg_inside`, it needs to match the
            // builder language direction and not the frontend one. Therefore we
            // must use `getBundle` from outside the iframe.
            const { getBundle } = window.parent.odoo.loader.modules.get("@web/core/assets");
            try {
                await Promise.all([
                    getBundle("website.assets_all_wysiwyg_inside").then(({ cssLibs, jsLibs }) =>
                        Promise.all([...cssLibs.map(loadCSS), ...jsLibs.map(loadJS)])
                    ),
                    loadBundle("website.assets_edit_frontend")
                ]);
            } catch (e){
                if (e instanceof AssetsLoadingError && e.cause instanceof TypeError) {
                    // an AssetsLoadingError caused by a TypeError means that the
                    // fetch request has been cancelled by the browser. It can occur
                    // when the user changes page, or navigate away from the website
                    // client action, so the iframe is unloaded. In this case, we
                    // don't care abour reporting the error, it is actually a normal
                    // situation.
                    return new Promise(() => {});
                } else {
                    throw e;
                }
            }
        }
        window.dispatchEvent(new CustomEvent('PUBLIC-ROOT-READY', {detail: {rootInstance}}));
    }
    return rootInstance;
});
lazyloader.registerPageReadinessDelay(prom);
export default prom;
