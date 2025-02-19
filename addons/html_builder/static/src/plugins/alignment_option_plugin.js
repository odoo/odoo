import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { classAction } from "../core/plugins/core_builder_action_plugin";

class AlignmentOptionPlugin extends Plugin {
    static id = "alignmentOption";
    resources = {
        builder_options: [
            {
                template: "html_builder.AlignmentOption",
                selector: ".s_share, .s_text_highlight, .s_social_media",
            },
        ],
        builder_actions: this.getActions(),
    };

    getActions() {
        return {
            setVerticalAlignment: {
                ...classAction,
                getPriority: ({ param: { mainParam: classNames } = { mainParam: "" } }) =>
                    classNames === "align-items-stretch" ? 0 : 1,
                isApplied: (...args) => {
                    const {
                        param: { mainParam: classNames },
                    } = args[0];
                    if (classNames === "align-items-stretch") {
                        return true;
                    }
                    return classAction.isApplied(...args);
                },
            },
        };
    }
}
registry.category("website-plugins").add(AlignmentOptionPlugin.id, AlignmentOptionPlugin);
