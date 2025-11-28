import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { BuilderAction } from "@html_builder/core/builder_action";

export class NewsletterLayoutOptionPlugin extends Plugin {
    static id = "newsletterLayoutOptionPlugin";

    resources = {
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
