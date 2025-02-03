import { Plugin } from "@html_editor/plugin";
import { getElementsWithOption } from "@html_builder/utils/utils";

export class SnippetLifecyclePlugin extends Plugin {
    static id = "snippetLifecyclePlugin";
    resources = {
        clean_for_save_handlers: this.cleanForSave.bind(this),
    };

    setup() {
        this.builderOptions = this.getResource("builder_options");
    }

    cleanForSave({ root }) {
        for (const option of this.builderOptions) {
            const { selector, exclude, cleanForSave } = option;
            if (!cleanForSave) {
                continue;
            }

            const editingEls = getElementsWithOption(root, selector, exclude);
            editingEls.forEach((editingEl) => cleanForSave(editingEl));
        }
    }
}
