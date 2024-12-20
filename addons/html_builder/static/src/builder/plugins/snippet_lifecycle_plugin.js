import { Plugin } from "@html_editor/plugin";

export class SnippetLifecyclePlugin extends Plugin {
    static id = "snippetLifecyclePlugin";
    static dependencies = ["visibilityPlugin"];
    resources = {
        clean_for_save_handlers: this.cleanForSave.bind(this),
    };

    setup() {
        this.builderOptions = this.getResource("builder_options");
    }

    cleanForSave({ root }) {
        for (const option of this.builderOptions) {
            const { selector, exclude, clean_for_save_handlers_options } = option;
            let editingEls = [...root.querySelectorAll(selector)];
            if (exclude) {
                editingEls = editingEls.filter((editingEl) => !editingEl.matches(exclude));
            }
            editingEls.forEach((editingEl) => {
                this.dependencies.visibilityPlugin.cleanForSaveVisibility(editingEl);
                if (clean_for_save_handlers_options) {
                    clean_for_save_handlers_options(editingEl);
                }
            });
        }
    }
}
