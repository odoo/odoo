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
        clean_for_save_processors: this.cleanForSave.bind(this),
        html_compatibility_processors: this.stripVersionMarkers.bind(this),
    };

    stripVersionMarkers(element) {
        if (element.matches(VERSION_SELECTOR) && element !== this.editable) {
            delete element.dataset.oeVersion;
        }
        stripVersion(element);
        return element;
    }

    cleanForSave(root) {
        const VERSIONS = htmlEditorVersions();
        const firstChild = root.firstElementChild;
        const version = VERSIONS.at(-1);
        if (firstChild && version) {
            firstChild.dataset.oeVersion = version;
        }
        return root;
    }
}
