import { contains } from "@web/../tests/web_test_helpers";
import { setupHTMLBuilder } from "@html_builder/../tests/helpers";
import { animationFrame, expect, test, queryOne, describe } from "@odoo/hoot";

describe.current.tags("desktop");

test("popover should only show the label and url inputs", async () => {
    const { getEditor } = await setupHTMLBuilder(
        '<p><a href="https://test.com/" class="btn btn-custom">Link label</a></p>'
    );
    getEditor().shared.selection.setSelection({
        anchorNode: queryOne(":iframe p > a"),
        anchorOffset: 1,
    });
    await contains(".o-we-linkpopover .o_we_edit_link").click();
    expect(".o-we-linkpopover .input-group").toHaveCount(2, {
        message: "Only the label and url inputs should be present",
    });
    expect(".o-we-linkpopover .o_we_label_link").toHaveValue("Link label");
    expect(".o-we-linkpopover .o_we_href_input_link").toHaveValue("https://test.com/");
    expect(".o-we-linkpopover [name='link_type']").toHaveCount(0);
    expect(".o-we-linkpopover [name='link_style_size']").toHaveCount(0);
    expect(".o-we-linkpopover [name='link_style_shape']").toHaveCount(0);
});

test("closing popover should not remove style", async () => {
    const { getEditor } = await setupHTMLBuilder(
        '<p><a href="https://test.com/" class="btn btn-custom" style="color: rgb(0, 255, 0);">Link label</a></p>'
    );
    getEditor().shared.selection.setSelection({
        anchorNode: queryOne(":iframe p > a"),
        anchorOffset: 1,
    });
    await contains(".o-we-linkpopover .o_we_edit_link").click();
    await contains(":iframe").click();

    expect(":iframe p > a").toHaveStyle("color: rgb(0, 255, 0)", { inline: true });
});

test("should load the current style", async () => {
    await setupHTMLBuilder(
        '<p><a href="http://test.com/" class="btn btn-secondary">Link label</a></p>',
        {
            styleContent:
                "p > a.btn { color: #ff0000; background-color: #00ff00; border: 5px dashed #0000ff; }",
        }
    );
    await contains(":iframe p > a").click();

    await contains("[data-label=Type] .o_hb_select_toggle").click();
    await contains(".o_popover .dropdown-item:contains('Custom')").click();

    expect(":iframe p > a").toHaveStyle(
        {
            "background-color": "rgb(0, 255, 0)",
            border: "5px dashed rgb(0, 0, 255)",
            color: "rgb(255, 0, 0)",
        },
        { inline: true }
    );
});

test("should load the current custom style correctly", async () => {
    await setupHTMLBuilder(
        '<p><a href="https://test.com/" class="btn btn-custom" style="color: rgb(0, 255, 0); background-color: rgb(0, 0, 255); border-width: 4px; border-color: rgb(255, 0, 0); border-style: dotted;">Link label</a></p>'
    );
    await contains(":iframe p > a").click();

    expect("[data-label=Type] .o_hb_select_toggle").toHaveText("Custom");
    expect("[data-label=Text] .o_we_color_preview").toHaveStyle("background-color: rgb(0, 255, 0)");
    expect("[data-label=Fill] .o_we_color_preview").toHaveStyle("background-color: rgb(0, 0, 255)");
    expect("[data-label=Border] .o_hb_input_number").toHaveValue("4");
    expect("[data-label=Border] .o_hb_select_toggle .o_hb_border_preview").toHaveStyle(
        "border-style: dotted",
        { inline: true }
    );
    expect("[data-label=Border] .o_we_color_preview").toHaveStyle(
        "background-color: rgb(255, 0, 0)"
    );
});

test("should not have the link option type", async () => {
    await setupHTMLBuilder('<p><a href="https://test.com/" class="btn">Link label</a></p>');

    await contains(":iframe p > a").click();

    await contains("[data-label=Type] .o_hb_select_toggle").click();

    expect(".o_popover .dropdown-item").toHaveCount(3);
    expect(".o_popover .dropdown-item:contains('Link')").toHaveCount(0);
});

test("should correctly set custom style on button", async () => {
    await setupHTMLBuilder('<p><a href="https://test.com/" class="btn">Link label</a></p>');

    await contains(":iframe p > a").click();

    await contains("[data-label=Type] .o_hb_select_toggle").click();
    await contains(".o_popover .dropdown-item:contains('Custom')").click();

    await contains("[data-label=Text] .o_we_color_preview").click();
    await contains(".o_color_button[data-color='#FF0000']").click();

    await contains("[data-label=Fill] .o_we_color_preview").click();
    await contains(".o_color_button[data-color='#00FF00']").click();

    await contains("[data-label=Border] .o_hb_input_number").edit("6");

    await contains("[data-label=Border] .o_we_color_preview").click();
    await contains(".o_color_button[data-color='#0000FF']").click();

    await contains("[data-label=Border] .o_hb_select_toggle").click();
    await contains(".o_popover .dropdown-item[data-action-value=dotted]").click();

    expect(":iframe p > a").toHaveClass("btn btn-custom");
    expect(":iframe p > a").toHaveStyle(
        {
            "background-color": "rgb(0, 255, 0)",
            border: "6px dotted rgb(0, 0, 255)",
            color: "rgb(255, 0, 0)",
        },
        { inline: true }
    );
});

test("should correctly set custom hover style on button", async () => {
    const { getEditor } = await setupHTMLBuilder(
        '<p><a href="https://test.com/" class="btn">Link label</a></p>'
    );

    await contains(":iframe p > a").click();

    await contains("[data-label=Type] .o_hb_select_toggle").click();
    await contains(".o_popover .dropdown-item:contains('Custom')").click();

    // A dark fill is shaded on hover
    await contains("[data-label=Fill] .o_we_color_preview").click();
    await contains(".o_color_button[data-color='#0000FF']").click();
    expect(":iframe p > a").toHaveStyle({ "--btn-custom-hover-bg": "#0000D9" });

    // A light fill is tinted on hover
    await contains("[data-label=Fill] .o_we_color_preview").click();
    await contains(".o_color_button[data-color='#FFFF00']").click();
    expect(":iframe p > a").toHaveStyle({ "--btn-custom-hover-bg": "#FFFF26" });

    // Switching to a non-custom type removes the hover background
    await contains("[data-label=Type] .o_hb_select_toggle").click();
    await contains(".o_popover .dropdown-item:contains('Button Primary')").click();
    expect(":iframe p > a").not.toHaveStyle("--btn-custom-hover-bg", { inline: true });

    const cleanedEl = getEditor().getElContent().querySelector("a.btn");
    expect(cleanedEl).not.toHaveStyle("--btn-custom-hover-bg", { inline: true });
});

test("outline custom button should only have a color option", async () => {
    await setupHTMLBuilder('<p><a href="https://test.com/" class="btn">Link label</a></p>', {
        styleContent:
            ":root { --o-color-1: #123456; } .text-o-color-1 { color: var(--o-color-1) !important; }",
    });

    await contains(":iframe p > a").click();

    await contains("[data-label=Type] .o_hb_select_toggle").click();
    await contains(".o_popover .dropdown-item:contains('Custom')").click();
    await contains("[data-label=Shape] .o_hb_select_toggle").click();
    await contains(".o_popover .dropdown-item:contains('Outline')").click();

    expect(":iframe p > a").toHaveClass("btn btn-outline-custom");
    expect("[data-label=Color]").toHaveCount(1);
    expect("[data-label=Text]").toHaveCount(0);
    expect("[data-label=Fill]").toHaveCount(0);

    await contains("[data-label=Color] .o_we_color_preview").click();
    await contains(".o_color_button[data-color='#FF0000']").click();
    expect(":iframe p > a").toHaveStyle({ "--btn-custom-color": "#FF0000" });
    expect("[data-label=Color] .o_we_color_preview").toHaveStyle(
        "background-color: rgb(255, 0, 0)"
    );

    await contains("[data-label=Color] .o_we_color_preview").click();
    await contains(".o_color_button[data-color='o-color-1']").click();
    expect(":iframe p > a").toHaveClass("text-o-color-1");
    expect("[data-label=Color] .o_we_color_preview").toHaveStyle(
        "background-color: rgb(18, 52, 86)"
    );
    await contains("[data-label=Color] .o_we_color_preview").click();
    expect(".o_color_button[data-color='o-color-1']").toHaveClass("selected");
});

test("fill gradient should be stored as background-image", async () => {
    await setupHTMLBuilder(
        '<p><a href="http://test.com/" class="btn btn-custom">Link label</a></p>'
    );

    await contains(":iframe p > a").click();

    await contains("[data-label=Fill] .o_we_color_preview").click();
    await contains(".gradient-tab").click();
    await contains(".o_gradient_color_button").click();

    expect(":iframe p > a").toHaveStyle(
        {
            "background-image":
                "linear-gradient(135deg, rgb(255, 204, 51) 0%, rgb(226, 51, 255) 100%)",
        },
        { inline: true }
    );
});

test("fill gradient should not be removed after text color change", async () => {
    await setupHTMLBuilder(
        '<p><a href="http://test.com/" class="btn btn-custom">Link label</a></p>'
    );

    await contains(":iframe p > a").click();

    const gradient = "linear-gradient(135deg, rgb(255, 204, 51) 0%, rgb(226, 51, 255) 100%)";
    await contains("[data-label=Fill] .o_we_color_preview").click();
    await contains(".gradient-tab").click();
    await contains(".o_gradient_color_button").click();

    expect(":iframe p > a").toHaveStyle({ "background-image": gradient }, { inline: true });

    // Change the text color and make sure the background gradient is preserved
    await contains("[data-label=Text] .o_we_color_preview").click();
    await contains(".o_color_button[data-color='#FF0000']").click();
    expect(":iframe p > a").toHaveStyle({ "background-image": gradient }, { inline: true });
});

test("border works even if current border style is none", async () => {
    await setupHTMLBuilder('<p><a href="http://test.com/" class="btn">Link label</a></p>', {
        styleContent: "p > a { border: 0px none rgba(0, 0, 0, 0); }",
    });

    await contains(":iframe p > a").click();

    await contains("[data-label=Type] .o_hb_select_toggle").click();
    await contains(".o_popover .dropdown-item:contains('Custom')").click();

    expect("[data-label=Border] .o_hb_input_number").toHaveValue("0");

    await contains("[data-label=Border] .o_hb_input_number").edit("4");
    await animationFrame();

    expect("[data-label=Border] .o_hb_input_number").toHaveValue("4");
    expect("[data-label=Border] .o_hb_select_toggle .o_hb_border_preview").toHaveStyle(
        "border-style: solid",
        { inline: true }
    );
    expect("[data-label=Border] .o_we_color_preview").toHaveStyle(
        "background-color: rgba(0, 0, 0, 0)",
        { inline: true }
    );
    expect(":iframe p > a").toHaveStyle(/border: 4px solid rgba(0, 0, 0, 0)/, { inline: true });

    await contains("[data-label=Border] .o_we_color_preview").click();
    await contains(".o_color_button[data-color='#0000FF']").click();

    await contains("[data-label=Border] .o_hb_select_toggle").click();
    await contains(".o_popover .dropdown-item[data-action-value=dotted]").click();

    expect(":iframe p > a").toHaveStyle(/border: 4px dotted rgb(0, 0, 255)/, { inline: true });
});
