import { expect, test } from "@odoo/hoot";
import { setupEditor } from "./_helpers/editor";
import { Plugin } from "@html_editor/plugin";
import { MAIN_PLUGINS } from "@html_editor/plugin_sets";

test("set o_editable_media class on contenteditable false media elements", async () => {
    class TestPlugin extends Plugin {
        static id = "test";
        resources = {
            force_not_editable_selector: "i",
            force_editable_selector: "i",
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
