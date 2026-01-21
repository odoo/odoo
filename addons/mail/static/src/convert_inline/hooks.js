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
export function useEmailHtmlConverter({ Plugins, bundles, target, debug }) {
    const cmp = useComponent();
    const converter = new EmailHtmlConverter(undefined, cmp.env.services);
    const layouts = {
        desktop: {
            document: undefined,
            reference: undefined,
            iframe: renderToElement("mail.EmailHtmlConverterReferenceIframe", {
                isBrowserSafari,
                isVisible: debug,
            }),
        },
        mobile: {
            document: undefined,
            reference: undefined,
            iframe: renderToElement("mail.EmailHtmlConverterReferenceIframe", {
                isBrowserSafari,
                isVisible: debug,
                width: "367px", // value used in the editor "mobile" mode
            }),
        },
    };
    target.append(layouts.desktop.iframe, layouts.mobile.iframe);
    const iframes = Object.values(layouts).map((layout) => layout.iframe);
    const assetsPromises = iframes.map((iframe) => loadIframeBundles(iframe, bundles));
    const contentPromises = [];
    for (const layout of Object.values(layouts)) {
        contentPromises.push(
            loadIframe(layout.iframe, () => {
                layout.document = layout.iframe.contentDocument;
                layout.document.head.append(renderToFragment("mail.EmailHtmlConverterHead"));
                // The iframe body must exactly have the iframe horizontal dimensions.
                layout.document.body.setAttribute(
                    "style",
                    `margin: 0 !important;
                    padding: 0 !important;`
                );
            })
        );
    }
    const iframesLoaded = Promise.all(contentPromises.concat(assetsPromises));
    iframesLoaded.catch((error) => {
        if (status(cmp) === "destroyed") {
            // Ignore loading errors if the Component was destroyed, since the
            // iframe was removed, there is nothing to load for.
            return;
        }
        throw error;
    });
    onWillDestroy(() => {
        converter.destroy();
        for (const iframe of iframes) {
            iframe.remove();
        }
    });
    return {
        cleanupEmailHtmlConversion: () => {
            for (const layout of Object.values(layouts)) {
                if (layout.reference?.isConnected) {
                    layout.reference.remove();
                }
            }
        },
        prepareEmailHtmlConversion: async (fragment) => {
            await iframesLoaded;
            this.cleanupEmailHtmlConversion();
            for (const layout of Object.values(layouts)) {
                layout.reference = renderToElement("mail.EmailHtmlConverterReference");
                layout.reference.append(fragment);
                layout.document.body.append(layout.reference);
            }
        },
        /**
         * @param {DocumentFragment} fragment reference content to convert as
         *        mail compliant HTML.
         * @param {Object} config config available to plugins during conversion.
         * @returns {string} mail compliant HTML.
         */
        convertToEmailHtml: async (fragment, config = {}) => {
            await this.prepareEmailHtmlConversion(fragment);
            return converter
                .convertToEmailHtml({
                    Plugins: Plugins ?? registry.category("mail-html-conversion-plugins").getAll(),
                    ...config,
                    ...layouts,
                })
                .then((emailHtml) => {
                    this.cleanupEmailHtmlConversion();
                    return emailHtml;
                });
        },
    };
}
