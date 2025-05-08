import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { withSequence } from "@html_editor/utils/resource";
import { CONTAINER_WIDTH } from "@website/builder/option_sequence";
import { ClassAction } from "@html_builder/core/core_builder_action_plugin";

class ContentWidthOptionPlugin extends Plugin {
    static id = "contentWidthOption";
    static dependencies = ["builderActions"];
    resources = {
        builder_options: [
            withSequence(CONTAINER_WIDTH, {
                template: "website.ContentWidthOption",
                selector: "section, .s_carousel .carousel-item, .s_carousel_intro_item",
                exclude:
                    "[data-snippet] :not(.oe_structure) > [data-snippet],#footer > *,#o_wblog_post_content *, .s_bento_banner section[data-name='Card'],.s_floating_blocks .s_floating_blocks_block, .s_bento_block_card",
                applyTo:
                    ":scope > .container, :scope > .container-fluid, :scope > .o_container_small",
            }),
        ],
        builder_actions: {
            SetContainerWidthAction,
        },
    };
}

export class SetContainerWidthAction extends ClassAction {
    static id = "setContainerWidth";
    apply({ isPreviewing, editingElement }) {
        super.apply(...arguments);
        editingElement.classList.toggle("o_container_preview", isPreviewing);
    }
}

registry.category("website-plugins").add(ContentWidthOptionPlugin.id, ContentWidthOptionPlugin);
