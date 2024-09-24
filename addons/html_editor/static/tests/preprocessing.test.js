import { Plugin } from "@html_editor/plugin";
import { MAIN_PLUGINS } from "@html_editor/plugin_sets";
import { expect, test } from "@odoo/hoot";
import { setupEditor } from "./_helpers/editor";
import { getContent } from "./_helpers/selection";

// we test here that plugins have a way to preprocess the dom BEFORE any editing
// action is done.
// The goal is to allow plugins such as knowledge to create a proper migration
// system, because it will likely have to load old documents using a previous
// format.

const migrations = [
    {
        from: "1",
        to: "2",
        update(elem) {
            elem.dataset.viewId = "34";
        },
    },
    {
        from: "2",
        to: "3",
        update(elem) {
            elem.dataset.actionId = "11";
        },
    },
];

class MigrationPlugin extends Plugin {
    static name = "knowledge_migrations_demo";
    resources = {
        preprocessDom: this.preprocessDom.bind(this),
    };

    preprocessDom(editable) {
        const elems = editable.querySelectorAll("[data-knowledge-version]");
        for (const elem of elems) {
            let version = elem.dataset.knowledgeVersion;
            for (const migration of migrations) {
                if (migration.from === version) {
                    migration.update(elem);
                    elem.dataset.knowledgeVersion = migration.to;
                    version = migration.to;
                }
            }
        }
    }
}

test("plugins can update DOM", async () => {
    const { el } = await setupEditor(`<p><span data-knowledge-version="1">content</span></p>`, {
        config: { Plugins: [...MAIN_PLUGINS, MigrationPlugin] },
    });
    expect(getContent(el)).toBe(
        `<p><span data-knowledge-version="3" data-view-id="34" data-action-id="11">content</span></p>`
    );
});
