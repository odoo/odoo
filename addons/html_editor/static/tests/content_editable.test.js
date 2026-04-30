import { expect, test } from "@odoo/hoot";
import { setupEditor } from "./_helpers/editor";
import { Plugin } from "@html_editor/plugin";
import { selectElements } from "@html_editor/utils/dom_traversal";

test("set o_editable_media class on contenteditable false media elements", async () => {
    class TestPlugin extends Plugin {
        static id = "test";
        resources = {
            content_not_editable_providers: (rootEl) => selectElements(rootEl, "i"),
            content_editable_providers: (rootEl) => selectElements(rootEl, "i"),
        };
    }
    await setupEditor(
        `
        <div class="wrapper" contenteditable="false"><i class="fa fa-shopping-cart fa-stack"></i></div>`,
        {
            config: { includePlugins: [TestPlugin] },
        }
    );
    expect(".wrapper > i").toHaveClass("o_editable_media");
    expect(".wrapper > i").toHaveAttribute("contenteditable", "false");
});
