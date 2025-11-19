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
export function useEmailHtmlConverter({ Plugins, bundles }) {
    const cmp = useComponent();
    const converter = new EmailHtmlConverter(undefined, cmp.env.services);
    const referenceIframe = renderToElement("mail.EmailHtmlConverterReferenceIframe", {
        isBrowserSafari,
    });
    document.body.append(referenceIframe);
    const onAssetsLoaded = loadIframeBundles(referenceIframe, bundles);
    loadIframe(referenceIframe, () => {
        referenceIframe.contentDocument.head.append(
            renderToFragment("mail.EmailHtmlConverterHead")
        );
        // The iframe body must exactly have the iframe horizontal dimensions.
        referenceIframe.contentDocument.body.setAttribute(
            "style",
            `margin: 0 !important;
            padding: 0 !important;`
        );
    });
    onAssetsLoaded.catch((error) => {
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
    return {
        // TODO EGGMAIL: return the function directly if there are other
        // tools needed.
        /**
         * @param {DocumentFragment} fragment reference content to convert as
         *        mail compliant HTML.
         * @param {Object} config config available to plugins during conversion.
         * @returns {string} mail compliant HTML.
         */
        convertToEmailHtml: async (fragment, config = {}) => {
            await onAssetsLoaded;
            const reference = renderToElement("mail.EmailHtmlConverterReference");
            reference.append(fragment);
            const referenceDocument = referenceIframe.contentDocument;
            referenceDocument.body.append(reference);
            return converter
                .convertToEmailHtml({
                    Plugins: Plugins ?? registry.category("mail-html-conversion-plugins").getAll(),
                    ...config,
                    reference,
                    referenceDocument,
                })
                .then((emailHtml) => {
                    reference.remove();
                    return emailHtml;
                });
        },
    };
}
