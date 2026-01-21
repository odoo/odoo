import { onWillDestroy, status, useComponent } from "@odoo/owl";
import { renderToElement, renderToFragment } from "@web/core/utils/render";
import { EmailHtmlConverter } from "@mail/convert_inline/email_html_converter";
import { registry } from "@web/core/registry";
import { loadIframeBundles, loadIframe } from "@mail/convert_inline/iframe_utils";
import { isBrowserSafari } from "@web/core/browser/feature_detection";

export const EMAIL_DESKTOP_DIMENSIONS = {
    width: 1320,
    height: 1000,
};
export const EMAIL_MOBILE_DIMENSIONS = {
    width: 367, // see `MassMailingIframe` mobile width
    height: 1000,
};

/**
 * Hook to handle email HTML conversion in a mail HtmlField.
 * @returns {Object} bundleControls, an object allowing to toggle bundles inside
 *          the conversion iframe, and convertToEmailHtml, a function to convert
 *          a reference fragment (field value inside a DIV) to mail compliant HTML.
 */
export function useEmailHtmlConverter({ Plugins, bundles, target, isVisible }) {
    let converter, reference, referenceDocument;
    let currentConfig = {};
    const cmp = useComponent();
    const referenceIframe = renderToElement("mail.EmailHtmlConverterReferenceIframe", {
        isBrowserSafari,
        isVisible,
    });
    target.append(referenceIframe);

    const updateLayoutDimensions = ({ width, height } = EMAIL_DESKTOP_DIMENSIONS) => {
        Object.assign(referenceIframe.style, {
            width: `${width}px !important`,
            minWidth: `${width}px !important`,
            height: `${height}px !important`,
            minHeight: `${height}px !important`,
        });
        if (converter) {
            converter.updateLayoutDimensions({ width, height });
        }
    };
    const cleanupEmailHtmlConversion = () => {
        if (reference?.isConnected) {
            reference.remove();
            reference = undefined;
        }
        if (converter) {
            converter.destroy();
            converter = undefined;
        }
    };
    const prepareEmailHtmlConversion = async (fragment) => {
        await iframeLoaded;
        cleanupEmailHtmlConversion();
        converter = new EmailHtmlConverter(undefined, cmp.env.services);
        reference = renderToElement("mail.EmailHtmlConverterReference");
        reference.append(fragment);
        referenceDocument.body.append(reference);
    };
    const getCurrentConfig = (newConfig) => {
        if (newConfig) {
            currentConfig = newConfig;
        }
        return {
            Plugins: Plugins ?? registry.category("mail-html-conversion-plugins").getAll(),
            ...currentConfig,
            reference,
            referenceDocument,
            updateLayoutDimensions,
        };
    };

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
        cleanupEmailHtmlConversion();
        referenceIframe.remove();
    });
    return {
        /**
         * @param {Object} dimensions
         * @param {Number} dimensions.width
         * @param {Number} dimensions.height
         */
        updateLayoutDimensions,
        /**
         * @param {DocumentFragment} fragment reference content to convert as
         *        mail compliant HTML.
         * @param {Object} [config] config available to plugins during conversion.
         * @returns {string} mail compliant HTML.
         */
        convertToEmailHtml: async (fragment, config) => {
            await prepareEmailHtmlConversion(fragment);
            const htmlConverted = converter.convertToEmailHtml(getCurrentConfig(config));
            if (!isVisible) {
                return htmlConverted.then((emailHtml) => {
                    cleanupEmailHtmlConversion();
                    return emailHtml;
                });
            }
            return htmlConverted;
        },
    };
}
