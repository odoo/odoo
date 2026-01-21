import { onWillDestroy, status, useComponent } from "@odoo/owl";
import { renderToElement, renderToFragment } from "@web/core/utils/render";
import { EmailHtmlConverter } from "@mail/convert_inline/email_html_converter";
import { registry } from "@web/core/registry";
import { loadIframeBundles, loadIframe } from "@mail/convert_inline/iframe_utils";
import { isBrowserSafari } from "@web/core/browser/feature_detection";

/**
 * Hook to handle email HTML conversion in a mail HtmlField.
 * @returns {Object} bundleControls, an object allowing to toggle bundles inside
 *          the conversion iframe, and convertToEmailHtml, a function to convert
 *          a reference fragment (field value inside a DIV) to mail compliant HTML.
 */
export function useEmailHtmlConverter({ Plugins, bundles, target, isVisible }) {
    const cmp = useComponent();
    const converter = new EmailHtmlConverter(undefined, cmp.env.services);
    const referenceIframe = renderToElement("mail.EmailHtmlConverterReferenceIframe", {
        isBrowserSafari,
        isVisible,
    });
    let referenceDocument;
    target.append(referenceIframe);
    const assetsPromise = loadIframeBundles(referenceIframe, bundles);
    const contentPromise = loadIframe(referenceIframe, () => {
        referenceDocument = referenceIframe.contentDocument;
        referenceDocument.head.append(renderToFragment("mail.EmailHtmlConverterHead"));
        // The iframe body must exactly have the iframe horizontal dimensions.
        referenceDocument.body.setAttribute(
            "style",
            `margin: 0 !important;
            padding: 0 !important;`
        );
    });
    const iframeLoaded = Promise.all([contentPromise, assetsPromise]);
    iframeLoaded.catch((error) => {
        if (status(cmp) === "destroyed") {
            // Ignore loading errors if the Component was destroyed, since the
            // iframe was removed, there is nothing to load for.
            return;
        }
        throw error;
    });
    onWillDestroy(() => {
        converter.destroy();
        referenceIframe.remove();
    });
    let reference;
    let currentConfig = {};
    return {
        cleanupEmailHtmlConversion: () => {
            if (reference?.isConnected) {
                reference.remove();
                reference = undefined;
            }
        },
        prepareEmailHtmlConversion: async (fragment) => {
            await iframeLoaded;
            this.cleanupEmailHtmlConversion();
            reference = renderToElement("mail.EmailHtmlConverterReference");
            reference.append(fragment);
            referenceDocument.body.append(reference);
        },
        getCurrentConfig(newConfig) {
            if (newConfig) {
                currentConfig = newConfig;
            }
            return {
                Plugins: Plugins ?? registry.category("mail-html-conversion-plugins").getAll(),
                ...currentConfig,
                reference,
                referenceDocument,
            };
        },
        /**
         * @param {DocumentFragment} fragment reference content to convert as
         *        mail compliant HTML.
         * @param {Object} config config available to plugins during conversion.
         * @returns {string} mail compliant HTML.
         */
        convertToEmailHtml: async (fragment, config = {}) => {
            await this.prepareEmailHtmlConversion(fragment);
            const htmlConverted = converter.convertToEmailHtml(this.getCurrentConfig(config));
            if (!isVisible) {
                return htmlConverted.then((emailHtml) => {
                    this.cleanupEmailHtmlConversion();
                    return emailHtml;
                });
            }
            return htmlConverted;
        },
    };
}
