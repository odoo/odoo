import {
    htmlEditorVersions,
    stripVersion,
    VERSION_SELECTOR,
} from "@html_editor/html_migrations/html_migrations_utils";
import { Plugin } from "@html_editor/plugin";

export class EditorVersionPlugin extends Plugin {
    static id = "editorVersion";
    /** @type {import("plugins").EditorResources} */
    resources = {
        clean_for_save_handlers: this.cleanForSave.bind(this),
        normalize_handlers: this.normalize.bind(this),
    };

    normalize(element) {
        if (element.matches(VERSION_SELECTOR) && element !== this.editable) {
            delete element.dataset.oeVersion;
        }
        stripVersion(element);
    }

    cleanForSave({ root }) {
        const VERSIONS = htmlEditorVersions();
        const firstChild = root.firstElementChild;
        const version = VERSIONS.at(-1);
        if (firstChild && version) {
            firstChild.dataset.oeVersion = version;
        }
    }
}
