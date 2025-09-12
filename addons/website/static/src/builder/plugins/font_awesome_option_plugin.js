import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { ClassAction } from "@html_builder/core/core_builder_action_plugin";
import { withSequence } from "@html_editor/utils/resource";
import { FONT_AWESOME } from "@html_builder/utils/option_sequence";
import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { BorderConfigurator } from "@html_builder/plugins/border_configurator_option";

class FontAwesomeOptionPlugin extends Plugin {
    static id = "fontAwesomeOptionPlugin";
    resources = {
        builder_options: [
            withSequence(FONT_AWESOME, {
                // converted to option component to handle rendering of
                // options based on the context(social media and share icons).
                OptionComponent: FontAwesomeOptionComponent,
                selector: "span.fa, i.fa",
                exclude: "[data-oe-xpath]",
            }),
        ],
        builder_actions: {
            FaResizeAction,
        },
    };
}

export class FaResizeAction extends ClassAction {
    static id = "faResize";
    apply(context) {
        const { editingElement } = context;
        editingElement.classList.remove("fa-1x", "fa-lg");
        super.apply(context);
    }
}
export class FontAwesomeOptionComponent extends BaseOptionComponent {
    static template = "website.FontAwesomeOption";
    static components = { BorderConfigurator };
    setup() {
        super.setup();
        this.state = useDomState((editingElement) => {
            const hasRestrictedClass =
                editingElement.closest(".s_social_media") || editingElement.closest(".s_share");
            return {
                showBackground: !hasRestrictedClass,
                showBorder: !hasRestrictedClass,
                showSize: !hasRestrictedClass,
            };
        });
    }
}

registry.category("website-plugins").add(FontAwesomeOptionPlugin.id, FontAwesomeOptionPlugin);
