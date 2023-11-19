import { test, expect } from "@odoo/hoot";
import { setupEditor } from "../_helpers/editor";
import { toggleCheckList } from "../_helpers/user_actions";
import { getContent } from "../_helpers/selection";
import { MAIN_PLUGINS } from "@html_editor/plugin_sets";
import { ChecklistIdsPlugin } from "@html_editor/main/list/checklist_ids_plugin";

test("should add a unique id on a new checklist", async () => {
    const { el, editor } = await setupEditor("<p>ab[]cd</p>", {
        config: { Plugins: [...MAIN_PLUGINS, ChecklistIdsPlugin] },
    });
    toggleCheckList(editor);
    editor.dispatch("ADD_STEP");
    const id = el.querySelector("li[data-check-id]").getAttribute("data-check-id");
    expect(getContent(el)).toBe(
        `<ul class="o_checklist"><li data-check-id="${id}">ab[]cd</li></ul>`
    );
});
