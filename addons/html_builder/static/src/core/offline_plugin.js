import { Plugin } from "@html_editor/plugin";
import { selectElements } from "@html_editor/utils/dom_traversal";

export class OfflinePlugin extends Plugin {
    static id = "offline";
    resources = {
        clean_for_save_handlers: this.cleanForSave.bind(this),
    };

    cleanForSave({ root }) {
        for (const el of selectElements(root, ".o_disabled_offline")) {
            el.classList.remove("o_disabled_offline");
        }
    }
}
