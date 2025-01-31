import { Plugin } from "@html_editor/plugin";

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

            let editingEls = [...root.querySelectorAll(selector)];
            if (root.matches(selector)) {
                editingEls.unshift(root);
            }
            if (exclude) {
                editingEls = editingEls.filter((editingEl) => !editingEl.matches(exclude));
            }
            editingEls.forEach((editingEl) => cleanForSave(editingEl));
        }
    }
}
