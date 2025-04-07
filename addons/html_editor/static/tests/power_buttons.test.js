import { describe, expect, test } from "@odoo/hoot";
import { click, press, tick, waitFor } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { setupEditor } from "./_helpers/editor";
import { getContent, setSelection } from "./_helpers/selection";
import { insertText } from "./_helpers/user_actions";
import { onRpc } from "@web/../tests/web_test_helpers";
import { Plugin } from "@html_editor/plugin";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { MAIN_PLUGINS } from "@html_editor/plugin_sets";
import { PowerboxPlugin } from "../src/main/powerbox/powerbox_plugin";

describe.tags("desktop");
describe("visibility", () => {
    test("should show power buttons on empty P tag", async () => {
        const { editor } = await setupEditor("<p>[]<br></p>");
        expect(".o_we_power_buttons").toBeVisible();
        insertText(editor, "a");
        await animationFrame();
        expect(".o_we_power_buttons").not.toBeVisible();
    });

    test("should not show power buttons on heading tags", async () => {
        await setupEditor("<h1>[]<br></h1>");
        expect(".o_we_power_buttons").not.toBeVisible();
    });

    test("should not show power buttons in table", async () => {
        await setupEditor(
            "<table><tbody><tr><td><p>[]<br></p></td><td><p><br></p></td></tr></tbody></table>"
        );
        expect(".o_we_power_buttons").not.toBeVisible();
    });

    test("should not show power buttons in banner", async () => {
        const { editor } = await setupEditor("<p>[]<br></p>");
        await waitFor(".o_we_power_buttons");
        insertText(editor, "/banner");
        press("enter");
        await animationFrame();
        expect(".o_we_power_buttons").not.toBeVisible();
    });

    test("should not show power buttons in columns", async () => {
        const { editor } = await setupEditor("<p>[]<br></p>");
        expect(".o_we_power_buttons").toBeVisible();
        insertText(editor, "/columns");
        press("enter");
        await animationFrame();
        expect(".o_we_power_buttons").not.toBeVisible();
    });

    test("should not show power buttons on empty p tag with text-align style", async () => {
        await setupEditor('<p style="text-align: right;">[]<br></p>');
        expect(".o_we_power_buttons").not.toBeVisible();
    });

    test("should not show power buttons on non empty block P tag", async () => {
        await setupEditor("<p>[]<br><br></p>");
        expect(".o_we_power_buttons").not.toBeVisible();
    });

    test("should not overlap with long placeholders", async () => {
        const placeholder = "This is a very very very very long placeholder";
        class TestPowerboxPlugin extends PowerboxPlugin {
            setup() {
                super.setup();
                this.resources.hints.text = placeholder;
            }
        }
        const tempP = document.createElement("p");
        tempP.innerText = placeholder;
        tempP.style.width = "fit-content";
        const Plugins = [...MAIN_PLUGINS.filter((p) => p.id !== "powerbox"), TestPowerboxPlugin];
        const { el } = await setupEditor("<p>[]<br></p>", {
            config: { Plugins },
        });
        el.appendChild(tempP);
        const placeholderWidth = tempP.getBoundingClientRect().width;
        el.removeChild(tempP);
        const powerButtons = document.querySelector(
            'div[data-oe-local-overlay-id="oe-power-buttons-overlay"]'
        );
        expect(powerButtons.getBoundingClientRect().left).toEqual(placeholderWidth + 20);
    });
});

describe.tags("desktop");
describe("buttons", () => {
    test("should create a numbered list using power buttons", async () => {
        const { el } = await setupEditor("<p>[]<br></p>");
        await click(".o_we_power_buttons .power_button.fa-list-ol");
        expect(getContent(el)).toBe(
            `<ol><li o-we-hint-text="List" class="o-we-hint">[]<br></li></ol>`
        );
    });

    test("should create a bullet list using power buttons", async () => {
        const { el } = await setupEditor("<p>[]<br></p>");
        await click(".o_we_power_buttons .power_button.fa-list-ul");
        expect(getContent(el)).toBe(
            `<ul><li o-we-hint-text="List" class="o-we-hint">[]<br></li></ul>`
        );
    });

    test("should create a check list using power buttons", async () => {
        const { el } = await setupEditor("<p>[]<br></p>");
        await click(".o_we_power_buttons .power_button.fa-check-square-o");
        expect(getContent(el)).toBe(
            `<ul class="o_checklist"><li o-we-hint-text="List" class="o-we-hint">[]<br></li></ul>`
        );
    });

    test("should open image selector using power buttons", async () => {
        onRpc("/web/dataset/call_kw/ir.attachment/search_read", () => [
            {
                id: 1,
                name: "logo",
                mimetype: "image/png",
                image_src: "/web/static/img/logo2.png",
                access_token: false,
                public: true,
            },
        ]);
        await setupEditor("<p>[]<br></p>");
        click(".o_we_power_buttons .power_button.fa-file-image-o");
        await animationFrame();
        expect(".o_select_media_dialog").toBeVisible();
    });

    test("should open link popover in 'button primary' mode using power buttons", async () => {
        await setupEditor("<p>[]<br></p>");
        click(".o_we_power_buttons .power_button.fa-square");
        await animationFrame();
        expect(".o-we-linkpopover").toHaveCount(1);
    });

    test("should open powerbox using power buttons", async () => {
        await setupEditor("<p>[]<br></p>");
        click(".o_we_power_buttons .power_button.oi-ellipsis-v");
        await animationFrame();
        expect(".o-we-powerbox").toHaveCount(1);
    });

    test("should open chatgpt dialog using power buttons", async () => {
        await setupEditor("<p>[]<br></p>");
        click(".o_we_power_buttons .power_button:contains('AI')");
        await animationFrame();
        expect(".modal .modal-header:contains('Generate Text with AI')").toHaveCount(1);
    });
});

describe.tags("desktop");
describe("individual button availability", () => {
    test("should not display button when isAvailable returns false", async () => {
        class TestPlugin extends Plugin {
            static id = "test";
            resources = {
                user_commands: {
                    id: "test",
                    title: "TestButton",
                    icon: "fa-bug",
                    isAvailable: ({ anchorNode }) =>
                        !closestElement(anchorNode, ".hide_test_button"),
                    run: () => {},
                },
                power_buttons: { commandId: "test" },
            };
        }
        const { el } = await setupEditor(`<p>[]<br></p><p class="hide_test_button"><br></p>`, {
            config: { Plugins: [...MAIN_PLUGINS, TestPlugin] },
        });
        expect(".o_we_power_buttons").toBeVisible();
        expect(".power_button.fa-bug").toBeVisible();

        // Place cursor in the second paragraph
        setSelection({ anchorNode: el.children[1], anchorOffset: 0 });
        await tick();

        expect(".o_we_power_buttons").toBeVisible();
        expect(".power_button.fa-bug").not.toBeVisible();
    });
});
