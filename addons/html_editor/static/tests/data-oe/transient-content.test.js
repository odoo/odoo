import { expect, test } from "@odoo/hoot";
import { setupEditor, testEditor } from "../_helpers/editor";

/**
 * @typedef { import("@html_editor/core/history_plugin").HistoryPlugin } HistoryPlugin
 */

test("should remove transient elements children during cleaning", async () => {
    await testEditor({
        contentBefore: '<div><p>a</p></div><div data-oe-transient-content="true"><p>a</p></div>',
        contentAfter: '<div><p>a</p></div><div data-oe-transient-content="true"></div>',
    });
});

test("should ignore transient elements children during serialization", async () => {
    const { el, editor } = await setupEditor(
        `<div><p>a</p></div><div data-oe-transient-content="true"><p>a</p></div>`
    );
    /** @type HistoryPlugin */
    const historyPlugin = editor.plugins.find((plugin) => plugin.constructor.name === "history");
    const node = historyPlugin.unserializeNode(historyPlugin.serializeNode(el));
    expect(node.innerHTML).toBe(`<div><p>a</p></div><div data-oe-transient-content="true"></div>`);
});
