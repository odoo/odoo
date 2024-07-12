import { expect, test } from "@odoo/hoot";
import { setupEditor } from "../_helpers/editor";

function insertTable(editor, cols, rows) {
    editor.dispatch("INSERT_TABLE", { cols, rows });
}

test("can insert a table", async () => {
    const { el, editor } = await setupEditor("<p>hello[]</p>", {});
    insertTable(editor, 4, 3);
    expect(el.querySelectorAll("tr").length).toBe(3);
    expect(el.querySelectorAll("td").length).toBe(12);
});
