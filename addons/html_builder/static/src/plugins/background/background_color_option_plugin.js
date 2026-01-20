import { BuilderAction } from "@html_builder/core/builder_action";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

/**
 * @typedef {((editingElement: HTMLElement) => void)[]} on_bg_color_updated_handlers
 */

export class BackgroundColorOptionPlugin extends Plugin {
    static id = "backgroundColorOption";
    resources = {
        builder_actions: {
            BgColorAction,
        },
    };
}

class BgColorAction extends BuilderAction {
    static id = "bgColor";
    apply({ editingElement }) {
        this.dispatchTo("on_bg_color_updated_handlers", editingElement);
    }
}

registry
    .category("builder-plugins")
    .add(BackgroundColorOptionPlugin.id, BackgroundColorOptionPlugin);
