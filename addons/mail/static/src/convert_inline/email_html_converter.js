import { getCSSRules, toInline } from "@mail/views/web/fields/html_mail_field/convert_inline";
import { renderToElement, renderToFragment } from "@web/core/utils/render";
import { loadIframe } from "@mail/convert_inline/iframe_utils";
import { isBrowserSafari } from "@web/core/browser/feature_detection";
import { PluginManager } from "@html_editor/plugin_manager";

export class EmailHtmlConverter extends PluginManager {
    setup() {
        super.setup();
        this.iframe = null;
        /** @type { HTMLElement } **/
        this.editable = null;
        /** @type { Document } **/
        this.document = null;
    }

    cleanup() {
        this.iframe.remove();
    }

    setupEditableIframe() {
        this.iframe = renderToElement("mail.EmailHtmlConverterEditableIframe", {
            isBrowserSafari,
        });
        this.config.referenceDocument.body.append(this.iframe);
    }

    setupEditable() {
        this.iframe.contentDocument.head.append(renderToFragment("mail.EmailHtmlConverterHead"));
        this.editable = this.iframe.contentDocument.body;
        this.document = this.iframe.contentDocument;
        // The iframe body must exactly have the iframe horizontal dimensions.
        this.editable.setAttribute(
            "style",
            `margin: 0 !important;
            padding: 0 !important;`
        );
    }

    /**
     * @param {MailHtmlConversionConfig} config
     */
    async convertToEmailHtml(config) {
        if (this.isDestroyed) {
            return;
        }
        this.setup();
        this.config = config;
        this.setupEditableIframe();
        await loadIframe(this.iframe, () => this.setupEditable());

        this.preparePlugins();
        this.startPlugins();
        this.isReady = true;

        const inlineValue = await this.htmlConversion();
        this.cleanup();
        return inlineValue;
    }

    getPluginContext() {
        return Object.assign(super.getPluginContext(...arguments), {
            document: this.document,
            editable: this.editable,
        });
    }

    getContent() {
        return this.getElContent().innerHTML;
    }

    getElContent() {
        return this.editable.cloneNode(true);
    }

    async htmlConversion() {
        // 1 load async content (i.e. image) for final dimensions
        await Promise.all(
            this.getResource("load_reference_content_handlers")
                .map((job) => job())
                .flat()
        );
        // 2 notify plugins that the reference is ready to be used as such (e.g. for style computations)
        this.getResource("reference_content_loaded_handlers").forEach((job) => job());

        // Old toInline
        // TODO EGGMAIL: adapt usage, use plugin instead of old method
        const cssRules = getCSSRules(this.config.referenceDocument);
        await toInline(this.config.reference, cssRules);
        return this.config.reference.innerHTML;

        // return this.getContent();
    }
}
