import { expect, test } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";
import { setupEditor } from "../_helpers/editor";
import { expandToolbar } from "../_helpers/toolbar";

test("should apply border color", async () => {
    await setupEditor(
        `<table class="o_selected_table"><tbody><tr>
            <td class="o_selected_td">11[]</td>
        </tr></tbody></table>`
    );
    await expandToolbar();
    await contains(".btn:has(.fa-pencil)").click();
    await contains("[data-color='#F7C6CE']").click();
    expect("td").toHaveStyle({ "border-color": "rgb(247, 198, 206)" }, { inline: true });
});

test("should apply border width", async () => {
    await setupEditor(`
        <table class="o_selected_table"><tbody><tr>
            <td class="o_selected_td">11[]</td>
        </tr></tbody></table>`);
    await expandToolbar();
    await contains(".btn[name='table_border_width']").click();
    await contains(".o-dropdown-item:has(.o-border-preview[style*='border-width: 3px'])").click();
    expect("td").toHaveStyle({ "border-width": "3px" }, { inline: true });
});

test("should apply border style", async () => {
    await setupEditor(`
        <table class="o_selected_table"><tbody><tr>
            <td class="o_selected_td">11[]</td>
        </tr></tbody></table>`);
    await expandToolbar();
    await contains(".btn[name='table_border_style']").click();
    await contains(
        ".o-dropdown-item:has(.o-border-preview[style*='border-style: dotted'])"
    ).click();
    expect("td").toHaveStyle({ "border-style": "dotted" }, { inline: true });
});

test("should remove only border color on color delete", async () => {
    await setupEditor(`
        <table class="o_selected_table"><tbody><tr>
            <td class="o_selected_td" style="border-color: #FF9C00; border-width: 1px; border-style: solid;">11[]</td>
        </tr></tbody></table>`);
    await expandToolbar();
    await contains(".btn:has(.fa-pencil)").click();
    await contains(".o_font_color_selector .fa-trash").click();
    expect("td").not.toHaveStyle("border-color", { inline: true });
    expect("td").toHaveStyle(
        {
            "border-width": "1px",
            "border-style": "solid",
        },
        { inline: true }
    );
});
