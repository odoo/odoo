import { SelectTemplate } from "@web_editor/js/editor/snippets.options";
import { registerWebsiteOption } from "@website/js/editor/snippets.registry";

export class MasonryLayout extends SelectTemplate {
    constructor() {
        super(...arguments);
        this.containerSelector = '> .container, > .container-fluid, > .o_container_small';
        this.selectTemplateWidgetName = 'masonry_template_opt';
    }

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Changes the container class according to the template.
     *
     * @see this.selectClass for parameters
     */
    selectContainerClass(previewMode, widgetValue, params) {
        const containerEl = this.$target[0].firstElementChild;
        const containerClasses = ["container", "container-fluid", "o_container_small"];
        containerEl.classList.remove(...containerClasses);
        containerEl.classList.add(widgetValue);
    }
}

registerWebsiteOption("MasonryLayout", {
    Class: MasonryLayout,
    template: "website.s_masonry_block_options",
    selector: ".s_masonry_block",
});
