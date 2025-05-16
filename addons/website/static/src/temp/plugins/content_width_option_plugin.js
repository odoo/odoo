import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { withSequence } from "@html_editor/utils/resource";
import { CONTAINER_WIDTH } from "@website/website_builder/option_sequence";

class ContentWidthOptionPlugin extends Plugin {
    static id = "contentWidthOption";
    static dependencies = ["builderActions", "history"];
    resources = {
        builder_options: [
            withSequence(CONTAINER_WIDTH, {
                template: "html_builder.ContentWidthOption",
                selector: "section, .s_carousel .carousel-item, .s_carousel_intro_item",
                exclude:
                    "[data-snippet] :not(.oe_structure) > [data-snippet],#footer > *,#o_wblog_post_content *",
                applyTo:
                    ":scope > .container, :scope > .container-fluid, :scope > .o_container_small",
            }),
        ],
        builder_actions: this.getActions(),
    };

    getActions() {
        const builderActions = this.dependencies.builderActions;
        const historyPlugin = this.dependencies.history;
        return {
            get setContainerWidth() {
                const classAction = builderActions.getAction("classAction");
                return {
                    ...classAction,
                    apply: (...args) => {
                        classAction.apply(...args);
                        // Add/remove the container preview.
                        const containerEl = args[0].editingElement;
                        const isPreviewMode = historyPlugin.getIsPreviewing();
                        containerEl.classList.toggle("o_container_preview", isPreviewMode);
                    },
                };
            },
        };
    }
}
registry.category("website-plugins").add(ContentWidthOptionPlugin.id, ContentWidthOptionPlugin);
