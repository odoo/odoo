import { registry } from "@web/core/registry";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { BuilderAction } from "@html_builder/core/builder_action";
import { after } from "@html_builder/utils/option_sequence";
import { WEBSITE_BACKGROUND_OPTIONS } from "@website/builder/option_sequence";

// TODO this should not be needed: the interaction of this snippet heavily
// relies on the size of its inner elements: it should restart on any change
// of the related options, at least... but this does not seem achievable without
// something like this (`getConfigurationSnapshot` does not work). Even changes
// of style/class on the main element does not restart the animation without
// overriding `getConfigurationSnapshot` in this case (?).
// See ANNOUNCEMENT_SCROLL_INTERACTION_RESTART.
class RestartInteraction extends BuilderAction {
    static id = "restartInteraction";
    static dependencies = ["edit_interaction"];

    apply({ editingElement, value, params }) {
        const snippetEl = editingElement.closest(".s_announcement_scroll");
        this.dependencies.edit_interaction.restartInteractions(snippetEl);
    }
}

class SetItemTextAction extends BuilderAction {
    static id = "setItemTextAction";
    static dependencies = ["edit_interaction"];

    getValue({ editingElement, params }) {
        return editingElement.textContent;
    }
    apply({ editingElement, value, params }) {
        editingElement.textContent = value;

        // TODO. See ANNOUNCEMENT_SCROLL_INTERACTION_RESTART.
        const snippetEl = editingElement.closest(".s_announcement_scroll");
        this.dependencies.edit_interaction.restartInteractions(snippetEl);
    }
}

export class AnnouncementScrollOptionPlugin extends Plugin {
    static id = "announcementScrollOptionPlugin";
    selector = "section.s_announcement_scroll";
    resources = {
        builder_options: [
            withSequence(after(WEBSITE_BACKGROUND_OPTIONS), {
                template: "website.AnnouncementScrollOption",
                selector: this.selector,
            }),
        ],
        builder_actions: {
            RestartInteraction,
            SetItemTextAction,
        },
    };
}

registry
    .category("website-plugins")
    .add(AnnouncementScrollOptionPlugin.id, AnnouncementScrollOptionPlugin);
