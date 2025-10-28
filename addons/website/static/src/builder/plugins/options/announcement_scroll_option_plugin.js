import { registry } from "@web/core/registry";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { BuilderAction } from "@html_builder/core/builder_action";
import { after } from "@html_builder/utils/option_sequence";
import { WEBSITE_BACKGROUND_OPTIONS } from "@website/builder/option_sequence";
import { BaseOptionComponent } from "@html_builder/core/utils";

class SetItemTextAction extends BuilderAction {
    static id = "setItemTextAction";
    static dependencies = ["edit_interaction"];

    getValue({ editingElement, params }) {
        return editingElement.textContent;
    }
    apply({ editingElement, value, params }) {
        editingElement.textContent = value;
    }
}

export class AnnouncementScrollOption extends BaseOptionComponent {
    static template = "website.AnnouncementScrollOption";
    static selector = "section.s_announcement_scroll";
}

export class AnnouncementScrollOptionPlugin extends Plugin {
    static id = "announcementScrollOptionPlugin";
    selector = AnnouncementScrollOption.selector;
    resources = {
        builder_options: [
            withSequence(after(WEBSITE_BACKGROUND_OPTIONS), AnnouncementScrollOption),
        ],
        builder_actions: {
            SetItemTextAction,
        },
    };
}

registry
    .category("website-plugins")
    .add(AnnouncementScrollOptionPlugin.id, AnnouncementScrollOptionPlugin);
