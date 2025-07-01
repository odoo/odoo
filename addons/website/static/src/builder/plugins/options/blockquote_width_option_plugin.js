import { classAction } from "@html_builder/core/core_builder_action_plugin";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

class BlockquoteWidthOptionPlugin extends Plugin {
    static id = "blockquoteWidthOption";
    static dependencies = ["builderActions"];
    resources = {
        builder_actions: {
            setBlockquoteAlignment: {
                ...classAction,
                isApplied: (...args) => {
                    const {
                        editingElement: el,
                        params: { mainParam: classNames },
                    } = args[0];
                    // Align-left button is active by default
                    if (classNames === "me-auto") {
                        return !["mx-auto", "ms-auto"].some((cls) => el.classList.contains(cls));
                    }
                    return classAction.isApplied(...args);
                },
            },
        },
    };
}

registry.category("website-plugins").add(BlockquoteWidthOptionPlugin.id, BlockquoteWidthOptionPlugin);
