// import { getCSSRules, toInline } from "@mail/views/web/fields/html_mail_field/convert_inline";
import { renderToElement, renderToFragment } from "@web/core/utils/render";
import { loadIframe } from "@mail/convert_inline/iframe_utils";
import { isBrowserSafari } from "@web/core/browser/feature_detection";
import { PluginManager } from "@html_editor/plugin_manager";
import { children } from "@html_editor/utils/dom_traversal";

export class EmailHtmlConverter extends PluginManager {
    setup() {
        super.setup();
        this.iframe = null;
        /** @type { HTMLElement } **/
        this.previewContainer = null;
        /** @type { Document } **/
        this.document = null;
    }

    cleanup() {
        this.iframe.remove();
    }

    setupPreviewContainerIframe() {
        this.iframe = renderToElement("mail.EmailHtmlConverterPreviewIframe", {
            isBrowserSafari,
        });
        this.config.referenceDocument.body.append(this.iframe);
    }

    setupPreviewContainer() {
        this.iframe.contentDocument.head.append(renderToFragment("mail.EmailHtmlConverterHead"));
        this.previewContainer = this.iframe.contentDocument.body;
        this.document = this.iframe.contentDocument;
        // The iframe body must exactly have the iframe horizontal dimensions.
        this.previewContainer.setAttribute(
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

        // TODO EGGMAIL: remove everything related to the "previewContainer"
        // if not necessary during the conversion process
        this.setupPreviewContainerIframe();
        await loadIframe(this.iframe, () => this.setupPreviewContainer());

        this.preparePlugins();
        this.startPlugins();
        this.isReady = true;

        const inlineTemplate = await this.htmlConversion();

        // Old toInline
        // TODO EGGMAIL: adapt usage, use plugin instead of old method
        // const cssRules = getCSSRules(this.config.referenceDocument);
        // await toInline(this.config.reference, cssRules);

        // TMP code to preview the value in an iframe
        const emailHTML = inlineTemplate.innerHTML;
        this.previewContainer.append(...children(inlineTemplate.content));

        this.cleanup();
        return emailHTML;
    }

    getPluginContext() {
        return Object.assign(super.getPluginContext(...arguments), {
            document: this.document,
            previewContainer: this.previewContainer,
        });
    }

    getEmailTemplate() {
        const template = this.config.referenceDocument.createElement("TEMPLATE");
        this.dispatchTo("render_email_html_handlers", template);
        // TODO EGGMAIL: post-process the template, or try to keep all the work before template generation?
        return template;
    }

    async htmlConversion() {
        // 1 load async content (i.e. image) for final dimensions
        await Promise.all(
            this.getResource("load_reference_content_handlers")
                .map((job) => job())
                .flat()
        );
        // 2 notify plugins that the reference is ready to be used as such (e.g. for style computations)
        this.dispatchTo("reference_content_loaded_handlers");

        const emailTemplate = this.getEmailTemplate();

        return emailTemplate;
    }
}
