// import { getCSSRules, toInline } from "@mail/views/web/fields/html_mail_field/convert_inline";
import { PluginManager } from "./plugin_manager";

export class EmailHtmlConverter extends PluginManager {
    /**
     * @param {MailHtmlConversionConfig} config
     */
    async convertToEmailHtml(config) {
        if (!(await this.measureReference(config))) {
            return null;
        }
        this.triggerTreeBuildingPhase();
        const inlineTemplate = this.triggerRenderingPhase();
        if (!inlineTemplate) {
            return null;
        }
        return inlineTemplate.innerHTML;

        // // Old toInline
        // // TODO EGGMAIL: adapt usage, use plugin instead of old method
        // const cssRules = getCSSRules(this.config.referenceDocument);
        // await toInline(this.config.reference, cssRules);
        // return this.config.reference.innerHTML;
    }

    async measureReference(config) {
        if (this.isDestroyed || this.scope.isDestroyed()) {
            return false;
        } else if (this.measureCompleted) {
            return this.isReady;
        }
        this.config = config;
        this.preparePlugins();
        this.startPlugins();
        this.isReady = true;
        await this.triggerMeasuringPhase();
        if (this.isDestroyed) {
            return false;
        }
        this.measureCompleted = true;
        return true;
    }

    async triggerMeasuringPhase() {
        // 1 prepare working environment, this is the only phase where reference
        // can be modified
        this.trigger("on_will_start_conversion_handlers");

        // TODO EGGMAIL: evaluate if we need another async step to communicate
        // with the server (eg to handle attachments) => instead of doing it
        // in the reference prior to calling htmlConversion.

        // 2 load async content (e.g. fonts and images) for final dimensions
        await Promise.all(this.trigger("on_load_reference_content_handlers").flat());
        if (this.isDestroyed) {
            return;
        }
        // 3 notify plugins that the reference is ready to be used as such (e.g. for style computations)
        this.trigger("on_measure_reference_content_handlers");
    }

    triggerTreeBuildingPhase() {
        // 4 build the render tree
        this.processThrough("build_render_tree_processors");
    }

    /**
     * Can be called multiple times to render new copies
     *
     * @returns {HTMLTemplateElement}
     */
    triggerRenderingPhase() {
        const template = this.config.referenceDocument.createElement("TEMPLATE");
        // 5 render the tree
        return this.processThrough("render_email_template_processors", template);
    }

    onLayoutDimensionsUpdated(dimensions) {
        this.trigger("on_layout_dimensions_updated_handlers", dimensions);
    }
}
