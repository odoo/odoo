// import { getCSSRules, toInline } from "@mail/views/web/fields/html_mail_field/convert_inline";
import { PluginManager } from "@html_editor/plugin_manager";

export class EmailHtmlConverter extends PluginManager {
    /**
     * @param {MailHtmlConversionConfig} config
     */
    async convertToEmailHtml(config) {
        if (this.isDestroyed) {
            return;
        }
        this.setup();
        this.config = config;

        this.preparePlugins();
        this.startPlugins();
        this.isReady = true;

        const inlineTemplate = await this.htmlConversion();

        // Old toInline
        // TODO EGGMAIL: adapt usage, use plugin instead of old method
        // const cssRules = getCSSRules(this.config.referenceDocument);
        // await toInline(this.config.reference, cssRules);

        return inlineTemplate.innerHTML;
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
