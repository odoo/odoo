import { describe, expect, test } from "@odoo/hoot";
import { click, press, waitFor } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { setupEditor } from "./_helpers/editor";
import { getContent } from "./_helpers/selection";
import { insertText } from "./_helpers/user_actions";
import { onRpc } from "@web/../tests/web_test_helpers";

describe.tags("desktop")("visibility", () => {
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
});

describe.tags("desktop")("buttons", () => {
    test("should create a numbered list using power buttons", async () => {
        const { el } = await setupEditor("<p>[]<br></p>");
        await click(".o_we_power_buttons .power_button.fa-list-ol");
        expect(getContent(el)).toBe(
            `<ol><li placeholder="List" class="o-we-hint">[]<br></li></ol>`
        );
    });

    test("should create a bullet list using power buttons", async () => {
        const { el } = await setupEditor("<p>[]<br></p>");
        await click(".o_we_power_buttons .power_button.fa-list-ul");
        expect(getContent(el)).toBe(
            `<ul><li placeholder="List" class="o-we-hint">[]<br></li></ul>`
        );
    });

    test("should create a check list using power buttons", async () => {
        const { el } = await setupEditor("<p>[]<br></p>");
        await click(".o_we_power_buttons .power_button.fa-check-square-o");
        expect(getContent(el)).toBe(
            `<ul class="o_checklist"><li placeholder="List" class="o-we-hint">[]<br></li></ul>`
        );
    });

    test("should open table selector using power buttons", async () => {
        await setupEditor("<p>[]<br></p>");
        click(".o_we_power_buttons .power_button.fa-table");
        await animationFrame();
        expect(".o-we-tablepicker").toBeVisible();
    });

    test("should open image selector using power buttons", async () => {
        onRpc("/web/dataset/call_kw/ir.attachment/search_read", () => {
            return [
                {
                    id: 1,
                    name: "logo",
                    mimetype: "image/png",
                    image_src: "/web/static/img/logo2.png",
                    access_token: false,
                    public: true,
                },
            ];
        });
        await setupEditor("<p>[]<br></p>");
        click(".o_we_power_buttons .power_button.fa-file-image-o");
        await animationFrame();
        expect(".o_select_media_dialog").toBeVisible();
    });

    test("should open link popover using power buttons", async () => {
        await setupEditor("<p>[]<br></p>");
        click(".o_we_power_buttons .power_button.fa-link");
        await animationFrame();
        expect(".o-we-linkpopover").toHaveCount(1);
    });

    test("should open powerbox using power buttons", async () => {
        await setupEditor("<p>[]<br></p>");
        click(".o_we_power_buttons .power_button.fa-ellipsis-v");
        await animationFrame();
        expect(".o-we-powerbox").toHaveCount(1);
    });
});
