import { before } from "@html_builder/utils/option_sequence";
import { NEWSLETTER_SELECT } from "@website/temp/website_mass_mailing/newsletter_subscribe_common_option_plugin";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { withSequence } from "@html_editor/utils/resource";

export class NewsletterLayoutOptionPlugin extends Plugin {
    static id = "newsletterLayoutOptionPlugin";
    static dependencies = ["builderActions"];

    resources = {
        builder_options: [
            withSequence(before(NEWSLETTER_SELECT), {
                template: "website_mass_mailing.NewsletterLayoutOption",
                selector: ".s_newsletter_block",
                applyTo:
                    ":scope > .container, :scope > .container-fluid, :scope > .o_container_small",
            }),
        ],
        builder_actions: this.getActions(),
    };

    getActions() {
        const getAction = this.dependencies.builderActions.getAction;
        return {
            selectNewsletterTemplate: {
                prepare: async ({ actionParam }) => {
                    await getAction("selectTemplate").prepare({ actionParam: actionParam });
                },
                isApplied: ({ editingElement, params: { attribute } }) => {
                    const parentEl = editingElement.parentElement;
                    return (
                        (!parentEl.dataset.newsletterTemplate && attribute === "email") ||
                        parentEl.dataset.newsletterTemplate === attribute
                    );
                },
                apply: (action) => {
                    getAction("selectTemplate").apply(action);
                    const parentEl = action.editingElement.parentElement;
                    parentEl.dataset.newsletterTemplate = action.params.attribute;
                },
                clean: (action) => getAction("selectTemplate").clean(action),
            },
        };
    }
}

registry
    .category("website-plugins")
    .add(NewsletterLayoutOptionPlugin.id, NewsletterLayoutOptionPlugin);
