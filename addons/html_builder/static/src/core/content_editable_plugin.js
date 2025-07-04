import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

/**
 * This plugin is responsible for setting the contenteditable attribute on some
 * elements. For example, on sections with a container, only the container
 * should be editable but not its sibling nodes in the section.
 * 
 * The force_editable_selector and force_not_editable_selector resources allow
 * other plugins to easily add editable or non editable elements.
 */
class ContentEditable extends Plugin {
    static id = "contentEditable";
    resources = {
        normalize_handlers: this.normalize.bind(this),
        force_not_editable_selector: [
            "section:has(> .o_container_small, > .container, > .container-fluid)",
        ],
        force_editable_selector: [
            "section > .o_container_small",
            "section > .container",
            "section > .container-fluid",
        ],
    };

    normalize(root) {
        const toDisableSelector = this.getResource("force_not_editable_selector").join(",");
        for(const toDisable of root.querySelectorAll(toDisableSelector)) {
            toDisable.setAttribute("contenteditable", "false");
        }

        const toEnableSelector = this.getResource("force_editable_selector").join(",");
        for(const toEnable of root.querySelectorAll(toEnableSelector)) {
            toEnable.setAttribute("contenteditable", "true");
        }
    }
}
registry.category("website-plugins").add(ContentEditable.id, ContentEditable);
