import { expect, test } from "@odoo/hoot";
import { setupEditor } from "./_helpers/editor";
import { Plugin } from "@html_editor/plugin";
import { MAIN_PLUGINS } from "@html_editor/plugin_sets";
import { selectElements } from "@html_editor/utils/dom_traversal";

test("set o_editable_media class on contenteditable false media elements", async () => {
    class TestPlugin extends Plugin {
        static id = "test";
        resources = {
            content_not_editable_providers: (rootEl) => [...selectElements(rootEl, "i")],
            content_editable_providers: (rootEl) => [...selectElements(rootEl, "i")],
        };
    }
    const Plugins = [...MAIN_PLUGINS, TestPlugin];
    await setupEditor(
        `
        <div class="wrapper"><i class="fa fa-shopping-cart fa-stack"></i></div>`,
        {
            config: { Plugins },
        }
    );
    expect(".wrapper > i").toHaveClass("o_editable_media");
    expect(".wrapper > i").toHaveAttribute("contenteditable", "false");
});
