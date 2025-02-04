import {
    htmlEditorVersions,
    stripVersion,
    VERSION_SELECTOR,
} from "@html_editor/html_migrations/manifest";
import { Plugin } from "@html_editor/plugin";

export class VersionPlugin extends Plugin {
    static id = "version";
    resources = {
        clean_for_save_handlers: this.cleanForSave.bind(this),
        normalize_handlers: this.normalize.bind(this),
    };

    normalize(parent) {
        if (parent.matches(VERSION_SELECTOR) && parent !== this.editable) {
            delete parent.dataset.oeVersion;
        }
        stripVersion(parent);
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
