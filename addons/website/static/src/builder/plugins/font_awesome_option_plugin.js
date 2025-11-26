import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { ClassAction } from "@html_builder/core/core_builder_action_plugin";
import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";

export class FontAwesomeOptionPlugin extends Plugin {
    static id = "fontAwesomeOptionPlugin";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_actions: {
            FaResizeAction,
        },
    };
}
registry.category("website-plugins").add(FontAwesomeOptionPlugin.id, FontAwesomeOptionPlugin);

export class FaResizeAction extends ClassAction {
    static id = "faResize";
    apply(context) {
        const { editingElement } = context;
        editingElement.classList.remove("fa-1x", "fa-lg");
        super.apply(context);
    }
}
export class FontAwesomeOption extends BaseOptionComponent {
    static id = "font_awesome_option";
    static template = "website.FontAwesomeOption";
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

registry.category("website-options").add(FontAwesomeOption.id, FontAwesomeOption);
