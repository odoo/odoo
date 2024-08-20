import { SelectTemplate } from "@web_editor/js/editor/snippets.options";
import { registerMassMailingOption } from "@mass_mailing/js/snippets.registry";

export class MasonryLayout extends SelectTemplate {
    constructor() {
        super(...arguments);
        this.containerSelector = '> .container, > .container-fluid, > .o_container_small';
        this.selectTemplateWidgetName = 'masonry_template_opt';
    }
}

registerMassMailingOption("MassMailingMasonryLayout", {
    Class: MasonryLayout,
    template: "mass_mailing.s_masonry_block_options",
    selector: ".s_masonry_block",
}, {
    sequence: 10,
});
