import { BasePlugin } from "@html_editor/base_plugin";
import { registry } from "@web/core/registry";

/**
 * Sometimes, reference elements, attributes or styles are discarded during
 * the conversion. This Plugin provides tools to reference content that was
 * not converted.
 *
 * TODO EGGMAIL: warn the user if content deemed "important" is discarded? Only
 * enable in debug? Only use in tests?
 */
export class EmailDiscardedContentPlugin extends BasePlugin {
    static id = "trash";
    static shared = ["add"];

    setup() {
        this.trashBin = {};
    }

    add(key, value) {
        this.trashBin[key] = this.trashBin[key] ?? [];
        this.trashBin[key].push(value);
    }
}

registry
    .category("mail-html-conversion-plugins")
    .add(EmailDiscardedContentPlugin.id, EmailDiscardedContentPlugin);
