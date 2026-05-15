import { onMounted, onPatched, onWillDestroy, onWillUnmount, useScope, status } from "@odoo/owl";
import { isBrowserSafari } from "@web/core/browser/feature_detection";
import { registry } from "@web/core/registry";
import { renderToElement, renderToFragment } from "@web/core/utils/render";
import { EmailHtmlConverter } from "@mail/convert_inline/email_html_converter";
import { loadIframeBundles, loadIframe } from "@mail/convert_inline/iframe_utils";
import { useService } from "@web/core/utils/hooks";

export const DIMENSIONS = {
    DESKTOP: Object.freeze({
        width: 1320,
        height: 1000,
    }),
    MOBILE: Object.freeze({
        width: 360,
        height: 1000,
    }),
};

/**
 * Hook to handle email HTML conversion in a mail HtmlField.
 * @param {Object} [options.targetRef] ref object with `el` property, container
 *                 for the iframe where the conversion will happen
 * @param {Array<string>} [options.bundles] bundles to load for the conversion
 * @returns {Object}
 */
export function useEmailHtmlConverter({ Plugins, bundles, services, targetRef, isVisible }) {
    let converter, reference, referenceDocument; // Element and Document in which the conversion takes place.
    let currentConfig = {};
    let isReady = false;
    const scope = useScope();
    const convertInlineIframeService = useService("convert_inline_iframe");
    const referenceIframe = renderToElement("mail.EmailHtmlConverterReferenceIframe", {
        isBrowserSafari,
        isVisible,
    });
    const {
        promise: iframeSetup,
        resolve: resolveIframeSetup,
        reject: rejectIframeSetup,
    } = Promise.withResolvers();

    const setupIframe = async () => {
        await convertInlineIframeService.readyPromise;
        if (status(scope.component) === "destroyed") {
            return;
        }
        convertInlineIframeService.add(referenceIframe, targetRef);
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
        await Promise.all([contentPromise, assetsPromise]);
        return true;
    };
    const updateLayoutDimensions = (dimensions = DIMENSIONS.DESKTOP) => {
        const { width, height } = dimensions;
        referenceIframe.style.setProperty("max-width", `${width}px`, "important");
        referenceIframe.style.setProperty("min-width", `${width}px`, "important");
        referenceIframe.style.setProperty("min-height", `${height}px`, "important");
        if (converter?.isReady) {
            converter.onLayoutDimensionsUpdated(dimensions);
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
    const unmountConverter = () => {
        isReady = false;
        cleanupEmailHtmlConversion();
    };
    const prepareEmailHtmlConversion = async (fragment) => {
        if (!(await iframeSetup)) {
            return false;
        }
        cleanupEmailHtmlConversion();
        converter = new EmailHtmlConverter(undefined, services);
        reference = renderToElement("mail.EmailHtmlConverterReference");
        reference.append(fragment);
        referenceDocument.body.append(reference);
        return true;
    };
    const getCurrentConfig = (newConfig) => {
        if (newConfig) {
            currentConfig = newConfig;
        }
        return {
            Plugins: Plugins ?? [
                ...registry.category("mail-html-conversion-core-plugins").getAll(),
                ...registry.category("mail-html-conversion-main-plugins").getAll(),
            ],
            ...currentConfig,
            reference,
            referenceDocument,
            updateLayoutDimensions,
        };
    };
    const convertToEmailHtml = async (fragment, config) => {
        if (!isReady || !(await prepareEmailHtmlConversion(fragment))) {
            return null;
        }
        if (!referenceIframe.isConnected) {
            unmountConverter();
            return null;
        }
        const htmlConverted = Promise.resolve(
            converter.convertToEmailHtml(getCurrentConfig(config))
        );
        if (!isVisible) {
            return htmlConverted.finally(() => {
                cleanupEmailHtmlConversion();
            });
        }
        return htmlConverted;
    };

    if (!targetRef) {
        setupIframe().then(resolveIframeSetup, rejectIframeSetup);
    }
    onMounted(() => {
        if (!targetRef || targetRef.el) {
            isReady = true;
        }
        if (targetRef?.el) {
            setupIframe().then(resolveIframeSetup, rejectIframeSetup);
        }
    });
    if (targetRef) {
        onPatched(() => {
            if (!targetRef.el) {
                unmountConverter();
            }
        });
    }
    onWillUnmount(unmountConverter);
    onWillDestroy(() => {
        resolveIframeSetup(false);
        referenceIframe.remove();
    });

    return {
        /**
         * @param {DocumentFragment} fragment reference content to convert as
         *        email compliant HTML.
         * @param {Object} [config]
         * @returns {Promise<string|null>} email compliant HTML.
         */
        convertToEmailHtml,
        /**
         * @param {Object} dimensions
         * @param {Number} dimensions.width
         * @param {Number} dimensions.height
         */
        updateLayoutDimensions,
    };
}
