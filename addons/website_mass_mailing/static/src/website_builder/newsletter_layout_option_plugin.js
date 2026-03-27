import { before } from "@html_builder/utils/option_sequence";
import { NEWSLETTER_SELECT } from "@website_mass_mailing/website_builder/newsletter_subscribe_common_option_plugin";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { withSequence } from "@html_editor/utils/resource";
import { BuilderAction } from "@html_builder/core/builder_action";
import { BaseOptionComponent } from "@html_builder/core/utils";

export class NewsletterLayoutOption extends BaseOptionComponent {
    static template = "website_mass_mailing.NewsletterLayoutOption";
    static selector = ".s_newsletter_block";
    static applyTo = ":scope > .container, :scope > .container-fluid, :scope > .o_container_small";
}

export class NewsletterLayoutOptionPlugin extends Plugin {
    static id = "newsletterLayoutOptionPlugin";
    static dependencies = ["builderActions"];

    resources = {
        builder_options: [withSequence(before(NEWSLETTER_SELECT),NewsletterLayoutOption)],
        builder_actions: {
            SelectNewsletterTemplateAction
        },
    };
}
export class SelectNewsletterTemplateAction extends BuilderAction {
    static id = "selectNewsletterTemplate";
    static dependencies = ["builderActions"];
    setup() {
        this.getAction = this.dependencies.builderActions.getAction;
    }
    async prepare({ actionParam }) {
        await this.getAction("selectTemplate").prepare({ actionParam: actionParam });
    }
    isApplied({ editingElement, params: { attribute } }) {
        const parentEl = editingElement.parentElement;
        return (
            (!parentEl.dataset.newsletterTemplate && attribute === "email") ||
            parentEl.dataset.newsletterTemplate === attribute
        );
    }
    apply(action) {
        this.getAction("selectTemplate").apply(action);
        const parentEl = action.editingElement.parentElement;
        parentEl.dataset.newsletterTemplate = action.params.attribute;
    }
    clean(action) {
        return this.getAction("selectTemplate").clean(action)
    }
}
registry
    .category("website-plugins")
    .add(NewsletterLayoutOptionPlugin.id, NewsletterLayoutOptionPlugin);
