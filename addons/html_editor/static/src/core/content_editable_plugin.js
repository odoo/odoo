import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";

/**
 * This plugin is responsible for setting the contenteditable attribute on some
 * elements.
 *
 * The force_editable_selector and force_not_editable_selector resources allow
 * other plugins to easily add editable or non editable elements.
 */

export class ContentEditablePlugin extends Plugin {
    static id = "contentEditablePlugin";
    resources = {
        normalize_handlers: withSequence(5, this.normalize.bind(this)),
    };

    normalize(root) {
        const toDisableSelector = this.getResource("force_not_editable_selector").join(",");
        for (const toDisable of root.querySelectorAll(toDisableSelector)) {
            toDisable.setAttribute("contenteditable", "false");
        }

        const toEnableSelector = this.getResource("force_editable_selector").join(",");
        for (const toEnable of root.querySelectorAll(toEnableSelector)) {
            toEnable.setAttribute("contenteditable", "true");
        }
    }
}
