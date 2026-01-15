import { describe, expect, test } from "@odoo/hoot";
import {
    click,
    edit,
    getActiveElement,
    hover,
    press,
    queryAll,
    queryFirst,
    queryOne,
    setInputRange,
    waitFor,
    waitUntil,
} from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { contains } from "@web/../tests/web_test_helpers";
import { setupEditor } from "./_helpers/editor";
import { getContent, setSelection } from "./_helpers/selection";
import { expandToolbar } from "./_helpers/toolbar";
import { execCommand } from "./_helpers/userCommands";
import { expectElementCount } from "./_helpers/ui_expectations";

test("can set foreground color", async () => {
    const { el } = await setupEditor("<p>[test]</p>");

    await expandToolbar();
    expect(".o_font_color_selector").toHaveCount(0);

    await click(".o-we-toolbar .o-select-color-foreground");
    await animationFrame();
    expect(".o_font_color_selector").toHaveCount(1);

    await click(".o_color_button[data-color='#6BADDE']");
    await animationFrame();
    await expectElementCount(".o-we-toolbar", 1);
    expect(".o_font_color_selector").toHaveCount(0); // selector closed
    expect(getContent(el)).toBe(`<p><font style="color: rgb(107, 173, 222);">[test]</font></p>`);
});

test("can set background color", async () => {
    const { el } = await setupEditor("<p>[test]</p>");

    await expandToolbar();
    expect(".o_font_color_selector").toHaveCount(0);

    await click(".o-select-color-background");
    await animationFrame();
    expect(".o_font_color_selector").toHaveCount(1);

    await click(".o_color_button[data-color='#6BADDE']");
    await animationFrame();
    await expectElementCount(".o-we-toolbar", 1);
    expect(".o_font_color_selector").toHaveCount(0); // selector closed
    expect(getContent(el)).toBe(
        `<p><font style="background-color: rgba(107, 173, 222, 0.6);">[test]</font></p>`
    );
});

test("should add opacity to custom background colors but not to theme colors", async () => {
    const { el } = await setupEditor("<p>[test]</p>");

    await expandToolbar();
    expect(".o_font_color_selector").toHaveCount(0);

    await contains(".o-select-color-background").click();
    expect(".o_font_color_selector").toHaveCount(1);

    await contains(".o_color_button[data-color='#FF0000']").click(); // Select a custom color.
    await expectElementCount(".o-we-toolbar", 1);
    expect(".o_font_color_selector").toHaveCount(0);
    // Verify custom color applies RGBA with 0.6 opacity.
    expect(getContent(el)).toBe(
        `<p><font style="background-color: rgba(255, 0, 0, 0.6);">[test]</font></p>`
    );
    // Verify paintbrush border bottom color has no opacity.
    expect("i.fa-paint-brush").toHaveStyle({ borderBottomColor: "rgb(255, 0, 0)" });

    await contains(".o-select-color-background").click();
    expect(".o_font_color_selector").toHaveCount(1);
    expect(".o_color_button[data-color='#FF0000']").toHaveClass("selected");

    await contains(".o_color_button[data-color='o-color-1']").click(); // Select a theme color
    await waitFor(".o-we-toolbar");
    expect(getContent(el)).toBe(`<p><font style="" class="bg-o-color-1">[test]</font></p>`);
    // Verify computed background color has no opacity.
    const backgroundColor = getComputedStyle(el.querySelector("p font")).backgroundColor;
    expect(backgroundColor).toBe("rgb(113, 75, 103)");
});

test("default opacity should get applied when applying background color to icon", async () => {
    const { el } = await setupEditor('<p>[ab<span class="fa fa-glass"></span>cd]</p>');

    await expandToolbar();
    expect(".o_font_color_selector").toHaveCount(0);

    await click(".o-select-color-background");
    await animationFrame();
    expect(".o_font_color_selector").toHaveCount(1);

    await click(".o_color_button[data-color='#FF0000']");
    await animationFrame();
    await expectElementCount(".o-we-toolbar", 1);
    expect(".o_font_color_selector").toHaveCount(0); // selector closed
    expect(getContent(el)).toBe(
        `<p><font style="background-color: rgba(255, 0, 0, 0.6);">[ab</font><font style="background-color: rgba(255, 0, 0, 0.6);">\ufeff<span class="fa fa-glass" contenteditable="false">\u200b</span>\ufeff</font><font style="background-color: rgba(255, 0, 0, 0.6);">cd]</font></p>`
    );
});

test("can render and apply color theme", async () => {
    await setupEditor("<p>[test]</p>");

    await expandToolbar();
    expect(".o_font_color_selector").toHaveCount(0);
    await click(".o-we-toolbar .o-select-color-foreground");
    await animationFrame();
    expect(".o_font_color_selector").toHaveCount(1);
    expect("button[data-color='o-color-1']").toHaveCount(1);
    expect(queryOne("button[data-color='o-color-1']").style.backgroundColor).toBe(
        "var(--o-color-1)"
    );

    expect(".text-o-color-1").toHaveCount(0);
    await click("button[data-color='o-color-1']");
    await waitFor(".text-o-color-1");
    expect(".text-o-color-1").toHaveCount(1);
});

test("can render and apply gradient color", async () => {
    await setupEditor("<p>[test]</p>");

    await expandToolbar();
    await click(".o-we-toolbar .o-select-color-foreground");
    await animationFrame();
    expect(queryOne("button[data-color='o-color-1']").style.backgroundColor).toBe(
        "var(--o-color-1)"
    );
    await click(".btn:contains('Gradient')");
    await animationFrame();
    await click(
        "button[data-color='linear-gradient(135deg, rgb(255, 204, 51) 0%, rgb(226, 51, 255) 100%)']"
    );
    await animationFrame();
    expect("i.fa-font").toHaveStyle({
        borderImage:
            "linear-gradient(135deg, rgb(255, 204, 51) 0%, rgb(226, 51, 255) 100%) 1 / 1 / 0 stretch",
    });
    expect("font.text-gradient").toHaveCount(1);
    expect("font.text-gradient").toHaveStyle({
        backgroundImage: "linear-gradient(135deg, rgb(255, 204, 51) 0%, rgb(226, 51, 255) 100%)",
    });
});

test("custom text-colors used in the editor are shown in the colorpicker", async () => {
    await setupEditor(
        `<p>
            <font style="color: rgb(255, 0, 0);">test</font>
            <font style="color: rgb(0, 255, 0);">[test]</font>
        </p>`
    );
    await expandToolbar();
    expect(".o_font_color_selector").toHaveCount(0);
    await click(".o-we-toolbar .o-select-color-foreground");
    await animationFrame();
    await click(".btn:contains('Custom')");
    await animationFrame();
    expect(".o_hex_input").toHaveValue("#00FF00");
    expect(queryAll("button[data-color='#ff0000']")).toHaveCount(1);
    expect(queryOne("button[data-color='#ff0000']").style.backgroundColor).toBe("rgb(255, 0, 0)");
    expect(queryAll("button[data-color='#00ff00']")).toHaveCount(1);
    expect(queryOne("button[data-color='#00ff00']").style.backgroundColor).toBe("rgb(0, 255, 0)");
});

test("custom background colors used in the editor are shown in the colorpicker", async () => {
    await setupEditor(
        `<p>
            <font style="background-color: rgb(255, 0, 0);">test</font>
            <font style="background-color: rgb(0, 255, 0);">[test]</font>
        </p>`
    );
    await expandToolbar();
    expect(".o_font_color_selector").toHaveCount(0);
    await click(".o-we-toolbar .o-select-color-background");
    await animationFrame();
    await click(".btn:contains('Custom')");
    await animationFrame();
    expect(".o_hex_input").toHaveValue("#00FF00");
    expect(queryAll("button[data-color='#ff0000']")).toHaveCount(1);
    expect(queryOne("button[data-color='#ff0000']").style.backgroundColor).toBe("rgb(255, 0, 0)");
    expect(queryAll("button[data-color='#00ff00']")).toHaveCount(1);
    expect(queryOne("button[data-color='#00ff00']").style.backgroundColor).toBe("rgb(0, 255, 0)");
});

test("applied custom color should be shown in colorpicker after switching tab", async () => {
    const { el } = await setupEditor(
        '<p><font style="background-color: rgb(255, 0, 0);">[test]</font></p>'
    );
    await expandToolbar();
    expect(".o_font_color_selector").toHaveCount(0);
    await click(".o-we-toolbar .o-select-color-background");
    await animationFrame();
    await click(".btn:contains('Custom')");
    await animationFrame();
    expect(".o_hex_input").toHaveValue("#FF0000");
    const newColor = "#00FF00";
    await contains(".o_hex_input").edit(newColor);
    expect(".o_hex_input").toHaveValue(newColor);
    expect(getContent(el)).toBe(
        '<p><font style="background-color: rgb(0, 255, 0);">test</font></p>'
    );
    await click(".btn:contains('Solid')");
    await animationFrame();
    await click(".btn:contains('Custom')");
    await animationFrame();
    expect(".o_hex_input").toHaveValue(newColor);
});

test("select hex color and apply it", async () => {
    const { el } = await setupEditor(`<p>[test]</p>`);
    await expandToolbar();
    expect(".o_font_color_selector").toHaveCount(0);

    await click(".o-we-toolbar .o-select-color-foreground");
    await animationFrame();
    expect(".o_font_color_selector").toHaveCount(1);

    await click(".btn:contains('Custom')");
    await animationFrame();
    await click(".o_hex_input");
    await animationFrame();
    expect(".o_font_color_selector").toHaveCount(1);

    await edit("#017E84"); // === rgb(1, 126, 132)
    await animationFrame();
    expect("button[data-color='#017E84']").toHaveCount(1);
    expect(queryOne("button[data-color='#017E84']").style.backgroundColor).toBe("rgb(1, 126, 132)");
    expect(getContent(el)).toBe(`<p><font style="color: rgb(1, 126, 132);">test</font></p>`);

    await click(".odoo-editor-editable");
    await animationFrame();
    expect(".o_font_color_selector").toHaveCount(0);
    expect(getContent(el)).toBe(`<p><font style="color: rgb(1, 126, 132);">[test]</font></p>`);
});

test("should be able to apply hex color with opacity component", async () => {
    const { el } = await setupEditor(`<p>[test]</p>`);
    await expandToolbar();
    expect(".o_font_color_selector").toHaveCount(0);

    await click(".o-we-toolbar .o-select-color-foreground");
    await animationFrame();
    expect(".o_font_color_selector").toHaveCount(1);

    await click(".btn:contains('Custom')");
    await animationFrame();
    await click(".o_hex_input");
    await animationFrame();
    expect(".o_font_color_selector").toHaveCount(1);

    await edit("#017E8480"); // === rgba(1, 126, 132, 0.5)
    await animationFrame();
    expect("button[data-color='#017E8480']").toHaveCount(1);
    expect(queryOne("button[data-color='#017E8480']").style.backgroundColor).toBe(
        "rgba(1, 126, 132, 0.5)"
    );
    expect(getContent(el)).toBe(`<p><font style="color: rgba(1, 126, 132, 0.5);">test</font></p>`);

    await click(".odoo-editor-editable");
    await animationFrame();
    expect(".o_font_color_selector").toHaveCount(0);
    expect(getContent(el)).toBe(
        `<p><font style="color: rgba(1, 126, 132, 0.5);">[test]</font></p>`
    );
});

test("custom color tab should be opened by default if selected color is a custom color", async () => {
    await setupEditor(`<p>a<font style="color: rgb(120, 100, 0, 0.6);">[test]</font>b</p>`);
    await expandToolbar();
    expect(".o_font_color_selector").toHaveCount(0);

    await click(".o-we-toolbar .o-select-color-foreground");
    await animationFrame();
    expect(".o_font_color_selector").toHaveCount(1);
    expect(".btn:contains('Custom')").toHaveClass("active");
});

test("gradient tab should be opened by default if selected color is a gradient color", async () => {
    await setupEditor(
        `<p>a<font style="background-image: linear-gradient(2deg, rgb(255, 204, 51) 10%, rgb(226, 51, 255) 90%);" class="text-gradient">[test]</font>b</p>`
    );
    await expandToolbar();
    expect(".o_font_color_selector").toHaveCount(0);

    await click(".o-we-toolbar .o-select-color-foreground");
    await animationFrame();
    expect(".o_font_color_selector").toHaveCount(1);
    expect(".btn:contains('Gradient')").toHaveClass("active");
});

test("solid color tab should be opened by default if selected color is a theme color", async () => {
    await setupEditor(`<p>a<font class="text-o-color-1">[test]</font>b</p>`);
    await expandToolbar();
    expect(".o_font_color_selector").toHaveCount(0);

    await click(".o-we-toolbar .o-select-color-foreground");
    await animationFrame();
    expect(".o_font_color_selector").toHaveCount(1);
    expect(".btn:contains('Solid')").toHaveClass("active");
});

test("always show the current custom color", async () => {
    const defaultTextColor = "rgb(1, 10, 100)";
    const styleContent = `* {color: ${defaultTextColor};}`;
    await setupEditor(`<p>[test]</p>`, { styleContent });
    await expandToolbar();
    await click(".o-we-toolbar .o-select-color-foreground");
    await animationFrame();

    await click(".btn:contains('Custom')");
    await animationFrame();
    await click(".o_hex_input");
    await animationFrame();
    expect(".o_colorpicker_section:nth-of-type(1) button").toHaveCount(1);
    expect(queryOne(".o_colorpicker_section:nth-of-type(1) button").style.backgroundColor).toBe(
        defaultTextColor,
        { message: "backgroundColor is the default black" }
    );

    await edit("#017E84"); // === rgb(1, 126, 132)
    await animationFrame();
    expect(".o_colorpicker_section:nth-of-type(1) button").toHaveCount(1);
    expect(queryOne(".o_colorpicker_section:nth-of-type(1) button").style.backgroundColor).toBe(
        "rgb(1, 126, 132)"
    );

    await hover(".o_colorpicker_section:nth-of-type(2) button:first");
    await animationFrame();
    expect(".o_colorpicker_section:first button").toHaveCount(1);
    expect(queryOne(".o_colorpicker_section:nth-of-type(1) button").style.backgroundColor).toBe(
        "rgb(1, 126, 132)"
    );
});

test("show applied text color selected in solid color tab", async () => {
    setupEditor(`<p><font style="color: rgb(255, 0, 0);">[test]</font></p>`);
    await expandToolbar();
    await click(".o-we-toolbar .o-select-color-foreground");
    await animationFrame();
    expect(".o_color_section .o_color_button.selected").toHaveCount(1);
    expect(queryOne(".o_color_section .o_color_button.selected").style.backgroundColor).toBe(
        "rgb(255, 0, 0)"
    );
    await contains("button[data-color='#0000FF']").click();
    await animationFrame();
    expect(".o_font_color_selector").toHaveCount(0);
    await click(".o-we-toolbar .o-select-color-foreground"); // Open color selector again
    await animationFrame();
    expect(".o_font_color_selector").toHaveCount(1);
    expect(".o_color_section .o_color_button.selected").toHaveCount(1);
    expect(queryOne(".o_color_section .o_color_button.selected").style.backgroundColor).toBe(
        "rgb(0, 0, 255)"
    );
});

test("Can reset a color", async () => {
    const { editor } = await setupEditor(
        `<p class="tested">
            <font style="color: rgb(255, 0, 0);">[test]</font>
        </p>`
    );
    await expandToolbar();
    expect("font[style='color: rgb(255, 0, 0);']").toHaveCount(1);
    expect(".tested").not.toHaveInnerHTML("test");
    await click(".o-we-toolbar .o-select-color-foreground");
    await animationFrame();
    await click("button.fa-trash");
    await animationFrame();
    expect("font[style='color: rgb(255, 0, 0);']").toHaveCount(0);
    expect(".tested").toHaveInnerHTML("test");
    execCommand(editor, "historyUndo");
    expect("font[style='color: rgb(255, 0, 0);']").toHaveCount(1);
    expect(".tested").not.toHaveInnerHTML("test");
});

test.tags("desktop");
test("selected text color is shown in the toolbar and update when hovering", async () => {
    await setupEditor(
        `<p>
            <font style="color: rgb(255, 0, 0);">[test]</font>
        </p>`
    );

    await expandToolbar();
    expect(".o_font_color_selector").toHaveCount(0);
    await animationFrame();
    expect("i.fa-font").toHaveStyle({ borderBottomColor: "rgb(255, 0, 0)" });
    await click(".o-we-toolbar .o-select-color-foreground");
    await animationFrame();
    // Hover a color
    await hover(queryOne("button[data-color='#FF00FF']"));
    await animationFrame();
    expect("i.fa-font").toHaveStyle({ borderBottomColor: "rgb(255, 0, 255)" });
    // Hover out
    await hover(queryOne(".o-we-toolbar .o-select-color-foreground"));
    await animationFrame();
    expect("i.fa-font").toHaveStyle({ borderBottomColor: "rgb(255, 0, 0)" });
});

test("selected text color is shown in the toolbar and update when clicking", async () => {
    await setupEditor(
        `<p>
            <font style="color: rgb(255, 0, 0);">[test]</font>
        </p>`
    );

    await expandToolbar();
    expect(".o_font_color_selector").toHaveCount(0);
    await animationFrame();
    expect("i.fa-font").toHaveStyle({ borderBottomColor: "rgb(255, 0, 0)" });
    await click(".o-we-toolbar .o-select-color-foreground");
    await animationFrame();
    await click("button[data-color='#FF00FF']");
    await animationFrame();
    expect("i.fa-font").toHaveStyle({ borderBottomColor: "rgb(255, 0, 255)" });
});
test("selected text color is not shown in the toolbar after removeFormat", async () => {
    const defaultTextColor = "rgb(1, 10, 100)";
    const styleContent = `* {color: ${defaultTextColor};}`;
    const { el } = await setupEditor(
        `<p>
            <font style="color: rgb(255, 0, 0);">t[es]t</font>
        </p>`,
        { styleContent }
    );

    await expandToolbar();
    expect(".o_font_color_selector").toHaveCount(0);
    expect("i.fa-font").toHaveStyle({ borderBottomColor: "rgb(255, 0, 0)" });
    await click(".btn .fa-eraser");
    await animationFrame();
    expect(getContent(el)).toBe(`<p>
            <font style="color: rgb(255, 0, 0);">t</font>[es]<font style="color: rgb(255, 0, 0);">t</font>
        </p>`);
    await animationFrame();
    expect("i.fa-font").toHaveStyle({ borderBottomColor: defaultTextColor });
});

test("selected color is shown and updates when selection change", async () => {
    const { el } = await setupEditor(
        `<p><font style="color: rgb(255, 156, 0);">test1</font> <font style="color: rgb(150, 255, 0);">[test2]</font></p>`
    );
    await expandToolbar();
    expect(".o_font_color_selector").toHaveCount(0);
    await animationFrame();
    expect("i.fa-font").toHaveStyle({ borderBottomColor: "rgb(150, 255, 0)" });
    setSelection({
        anchorNode: el.firstChild,
        anchorOffset: 0,
        focusNode: el.firstChild,
        focusOffset: 1,
    });
    await waitUntil(() => queryOne("i.fa-font").style.borderBottomColor === "rgb(255, 156, 0)");
    expect("i.fa-font").toHaveStyle({ borderBottomColor: "rgb(255, 156, 0)" });
});

test("selected background color is shown in the toolbar and update when clicking", async () => {
    await setupEditor(
        `<p>
            <font style="background: rgb(255, 0, 0);">[test]</font>
        </p>`
    );

    await expandToolbar();
    await animationFrame();
    expect("i.fa-paint-brush").toHaveStyle({ borderBottomColor: "rgb(255, 0, 0)" });
    await click(".o-select-color-background");
    await animationFrame();
    await click("button[data-color='#FF00FF']");
    await animationFrame();
    expect("i.fa-paint-brush").toHaveStyle({ borderBottomColor: "rgb(255, 0, 255)" });
});

test("clicking on button color parent does not crash", async () => {
    const { el } = await setupEditor("<p>[test]</p>");

    await expandToolbar();
    await click(".o-we-toolbar .o-select-color-foreground");
    await animationFrame();
    await click(".o_colorpicker_section");
    await animationFrame();
    await click(".o_color_button[data-color='#6BADDE']");
    await animationFrame();
    expect(getContent(el)).toBe(`<p><font style="color: rgb(107, 173, 222);">[test]</font></p>`);
});

test("gradient picker should be closed by default when switching gradient tab", async () => {
    await setupEditor("<p>[test]</p>");

    await expandToolbar();
    await click(".o-we-toolbar .o-select-color-foreground");
    await animationFrame();
    expect(".o_font_color_selector").toHaveCount(1);
    await click(".btn:contains('Gradient')");
    await animationFrame();
    expect(".o_colorpicker_widget").toHaveCount(0);
    await click("button[title='Define a custom gradient']");
    await animationFrame();
    expect(".o_colorpicker_widget").toHaveCount(1);
    await click("button[title='Define a custom gradient']"); // Should be toggleable
    await animationFrame();
    expect(".o_colorpicker_widget").toHaveCount(0);
});

test("gradient picker correctly shows the current selected gradient", async () => {
    await setupEditor(
        `<p><font style="background-image: linear-gradient(2deg, rgb(255, 204, 51) 10%, rgb(226, 51, 255) 90%);" class="text-gradient">[test]</font></p>`
    );
    await expandToolbar();
    expect(".o_font_color_selector").toHaveCount(0);
    await click(".o-we-toolbar .o-select-color-foreground");
    await animationFrame();
    await click("button[title='Define a custom gradient']");
    await animationFrame();
    expect("button.active:contains('Linear')").toHaveCount(1);
    expect("input[name='angle']").toHaveValue(2);
    expect("input[name='custom gradient percentage color 1']").toHaveValue(10);
    expect("input[name='custom gradient percentage color 2']").toHaveValue(90);
});

test("custom colorpicker should show default color when selected text has gradient", async () => {
    await setupEditor(
        `<p><font style="background-image: linear-gradient(2deg, rgb(255, 204, 51) 10%, rgb(226, 51, 255) 90%);" class="text-gradient">[test]</font></p>`
    );
    await expandToolbar();
    expect(".o_font_color_selector").toHaveCount(0);
    await click(".o-we-toolbar .o-select-color-foreground");
    await expectElementCount(".o_font_color_selector", 1);
    await click(".btn:contains('Custom')");
    await expectElementCount(".o_hex_input", 1);
    expect(".o_hex_input").toHaveValue("#FF0000");
});

test("gradient picker does change the selector gradient color", async () => {
    await setupEditor(
        `<p><font style="background-image: linear-gradient(2deg, rgb(255, 204, 51) 10%, rgb(226, 51, 255) 90%);" class="text-gradient">[test]</font></p>`
    );
    await expandToolbar();
    expect(".o_font_color_selector").toHaveCount(0);
    await click(".o-we-toolbar .o-select-color-foreground");
    await animationFrame();
    await click("button[title='Define a custom gradient']");
    await animationFrame();
    expect("button.active:contains('Linear')").toHaveCount(1);
    await contains("input[name='angle']").edit("10");
    await setInputRange("input[name='custom gradient percentage color 1']", 30);
    await setInputRange("input[name='custom gradient percentage color 2']", 50);
    expect("font.text-gradient").toHaveStyle({
        backgroundImage: "linear-gradient(10deg, rgb(255, 204, 51) 30%, rgb(226, 51, 255) 50%)",
    });
});

test("gradient picker allow adding gradient color", async () => {
    await setupEditor(
        `<p><font style="background-image: linear-gradient(2deg, rgb(255, 0, 255) 10%, rgb(0, 255, 0) 90%);" class="text-gradient">[test]</font></p>`
    );
    await expandToolbar();
    expect(".o_font_color_selector").toHaveCount(0);
    await click(".o-we-toolbar .o-select-color-foreground");
    await animationFrame();
    await click("button[title='Define a custom gradient']");
    await animationFrame();
    await click(".btn:contains('Gradient')");
    await animationFrame();
    expect("button.active:contains('Linear')").toHaveCount(1);
    await click(".custom-gradient-configurator .gradient-preview");
    await animationFrame();
    expect("input[name='custom gradient percentage color 1']").toHaveValue(10);
    expect("input[name='custom gradient percentage color 2']").toHaveValue(50); // todo simulate click position ?
    expect("input[name='custom gradient percentage color 3']").toHaveValue(90);
    expect("font.text-gradient").toHaveStyle({
        backgroundImage:
            "linear-gradient(2deg, rgb(255, 0, 255) 10%, rgb(128, 128, 128) 50%, rgb(0, 255, 0) 90%)",
    });
});

test("clicking on the angle input does not close the dropdown", async () => {
    await setupEditor(
        `<p><font style="background-image: linear-gradient(2deg, rgb(255, 204, 51) 10%, rgb(226, 51, 255) 90%);" class="text-gradient">[test]</font></p>`
    );
    await expandToolbar();
    expect(".o_font_color_selector").toHaveCount(0);
    await click(".o-we-toolbar .o-select-color-foreground");
    await animationFrame();
    await click("button[title='Define a custom gradient']");
    await animationFrame();
    expect("button.active:contains('Linear')").toHaveCount(1);
    await contains("input[name='angle'").click();
    expect("input[name='angle'").toHaveCount(1);
});

test("should be able to select farthest-corner option in radial gradient", async () => {
    await setupEditor(`<p>a[bcd]e</p>`);
    await expandToolbar();
    await click(".o-we-toolbar .o-select-color-foreground");
    await animationFrame();
    expect(".btn:contains('Gradient')").toHaveCount(1);
    await click(".btn:contains('Gradient')");
    await animationFrame();
    await click("button[title='Define a custom gradient']");
    await animationFrame();
    expect("button:contains('Radial')").toHaveCount(1);
    await click(".btn:contains('Radial')");
    await animationFrame();
    expect("button[title='Extend to the farthest corner']").toHaveCount(1);
    await click("button[title='Extend to the farthest corner']");
    await animationFrame();
    expect("button[title='Extend to the farthest corner']").toHaveClass("active");
});

test("solid tab color navigation using keys", async () => {
    const { el } = await setupEditor("<p>[test]</p>");
    await expandToolbar();
    await click(".o-we-toolbar .o-select-color-foreground");
    await animationFrame();
    await press("Tab");
    expect(getActiveElement()).toBe(queryFirst('.o_font_color_selector button:contains("Custom")'));
    await press("Tab");
    expect(getActiveElement()).toBe(
        queryFirst('.o_font_color_selector button:contains("Gradient")')
    );
    await press("Tab");
    expect(getActiveElement()).toBe(queryFirst(".o_font_color_selector button.fa-trash"));
    await press("Tab");
    expect(getActiveElement()).toBe(
        queryFirst('.o_font_color_selector button[data-color="o-color-1"]')
    );
    await press("ArrowDown");
    expect(getActiveElement()).toBe(
        queryFirst('.o_font_color_selector button[data-color="#000000"]')
    );
    await press("ArrowRight");
    expect(getActiveElement()).toBe(
        queryFirst('.o_font_color_selector button[data-color="#424242"]')
    );
    await press("ArrowDown");
    expect(getActiveElement()).toBe(
        queryFirst('.o_font_color_selector button[data-color="#FF9C00"]')
    );
    await press("ArrowLeft");
    expect(getActiveElement()).toBe(
        queryFirst('.o_font_color_selector button[data-color="#FF0000"]')
    );
    await press("ArrowUp");
    expect(getActiveElement()).toBe(
        queryFirst('.o_font_color_selector button[data-color="#000000"]')
    );
    await press("Enter");
    expect(getContent(el)).toBe(`<p><font style="color: rgb(0, 0, 0);">[test]</font></p>`);
});

test("custom tab color navigation using keys", async () => {
    const { el } = await setupEditor("<p>[test]</p>");
    await expandToolbar();
    await click(".o-we-toolbar .o-select-color-foreground");
    await animationFrame();
    await click(".o_color_button[data-color='#FF0000']");
    await animationFrame();
    await click(".o-we-toolbar .o-select-color-foreground");
    await animationFrame();
    await press("Tab");
    expect(getActiveElement()).toBe(queryFirst('.o_font_color_selector button:contains("Custom")'));
    await press("Enter");
    await animationFrame();
    expect(".btn:contains('Custom')").toHaveClass("active");
    await press("Tab");
    await press("Tab");
    await press("Tab");
    expect(getActiveElement()).toBe(
        queryFirst(`.o_font_color_selector button[data-color="#ff0000"]`)
    );
    await press("ArrowDown");
    expect(getActiveElement()).toBe(
        queryFirst('.o_font_color_selector button[data-color="black"]')
    );
    await press("ArrowDown");
    expect(getActiveElement()).toBe(
        queryFirst('.o_font_color_selector button[data-color="black"]') // Should do nothing
    );
    await press("Enter");
    expect(getContent(el)).toBe(`<p><font style="" class="text-black">[test]</font></p>`);
});

describe.tags("desktop");
describe("keyboard navigation", () => {
    test("update saturation and brightness picker with keys", async () => {
        await setupEditor(
            `<p>
                <font style="color: rgb(255, 0, 0);">[test]</font>
            </p>`
        );
        await expandToolbar();
        await click(".o-we-toolbar .o-select-color-foreground");
        await animationFrame();
        await press("Tab");
        expect(getActiveElement()).toBe(
            queryFirst('.o_font_color_selector button:contains("Custom")')
        );
        await press("Enter");
        await animationFrame();
        await press("Tab", { shiftKey: true });
        await press("Tab", { shiftKey: true });
        await press("Tab", { shiftKey: true });
        await press("Tab", { shiftKey: true });
        await press("Tab", { shiftKey: true });
        expect(getActiveElement()).toBe(queryFirst(".o_font_color_selector .o_picker_pointer"));
        expect(".o_hex_input").toHaveValue("#FF0000");
        await press("ArrowUp");
        expect(".o_hex_input").toHaveValue("#FF3333");
        await press("ArrowLeft");
        expect(".o_hex_input").toHaveValue("#F53D3D");
        await press("ArrowDown");
        expect(".o_hex_input").toHaveValue("#F20D0D");
        await press("ArrowRight");
        expect(".o_hex_input").toHaveValue("#FF0000");
    });

    test("update hue slider with keys", async () => {
        await setupEditor(
            `<p>
                <font style="color: rgb(0, 255, 0);">[test]</font>
            </p>`
        );
        await expandToolbar();
        await click(".o-we-toolbar .o-select-color-foreground");
        await animationFrame();
        await press("Tab");
        expect(getActiveElement()).toBe(
            queryFirst('.o_font_color_selector button:contains("Custom")')
        );
        await press("Enter");
        await animationFrame();
        await press("Tab", { shiftKey: true });
        await press("Tab", { shiftKey: true });
        await press("Tab", { shiftKey: true });
        await press("Tab", { shiftKey: true });
        expect(getActiveElement()).toBe(queryFirst(".o_font_color_selector .o_slider_pointer"));
        expect(".o_hex_input").toHaveValue("#00FF00");
        await press("ArrowUp");
        expect(".o_hex_input").toHaveValue("#00FF2A");
        await press("ArrowDown");
        expect(".o_hex_input").toHaveValue("#00FF00");
        await press("ArrowRight");
        expect(".o_hex_input").toHaveValue("#00FF2A");
        await press("ArrowLeft");
        expect(".o_hex_input").toHaveValue("#00FF00");
        await press("PageUp");
        expect(".o_hex_input").toHaveValue("#00FF80");
        await press("PageDown");
        expect(".o_hex_input").toHaveValue("#00FF00");
        await press("Home");
        expect(".o_hex_input").toHaveValue("#FF0000");
        await press("ArrowUp");
        expect(".o_hex_input").not.toHaveValue("#FF0000");
        await press("End");
        expect(".o_hex_input").toHaveValue("#FF0000");
    });

    test("update opacity slider with keys", async () => {
        await setupEditor(
            `<p>
                <font style="color: rgb(255, 0, 0);">[test]</font>
            </p>`
        );
        await expandToolbar();
        await click(".o-we-toolbar .o-select-color-foreground");
        await animationFrame();
        await press("Tab");
        expect(getActiveElement()).toBe(
            queryFirst('.o_font_color_selector button:contains("Custom")')
        );
        await press("Enter");
        await animationFrame();
        await press("Tab", { shiftKey: true });
        await press("Tab", { shiftKey: true });
        await press("Tab", { shiftKey: true });
        expect(getActiveElement()).toBe(queryFirst(".o_font_color_selector .o_opacity_pointer"));
        expect(".o_hex_input").toHaveValue("#FF0000");
        await press("ArrowDown");
        expect(".o_hex_input").toHaveValue("#FF0000E6");
        await press("ArrowLeft");
        expect(".o_hex_input").toHaveValue("#FF0000CC");
        await press("Home");
        expect(".o_hex_input").toHaveValue("#FF000000");
        await press("ArrowUp");
        expect(".o_hex_input").toHaveValue("#FF00001A");
        await press("ArrowRight");
        expect(".o_hex_input").toHaveValue("#FF000033");
        await press("End");
        expect(".o_hex_input").toHaveValue("#FF0000");
    });

    test("click on saturation and brightness picker sets implicit focus on it", async () => {
        await setupEditor("<p>[test]</p>");
        await expandToolbar();
        await click(".o-we-toolbar .o-select-color-foreground");
        await animationFrame();
        await contains('.o_font_color_selector button:contains("Custom")').click();
        await contains(".o_font_color_selector .o_color_pick_area").click();
        await press("Tab");
        expect(getActiveElement()).toBe(queryFirst(".o_font_color_selector .o_slider_pointer"));
        await contains(".o_font_color_selector .o_color_pick_area").click({
            position: { top: 0, left: 0 }, // other positions don't guarantee a fixed color
            relative: true,
        });
        expect(".o_hex_input").toHaveValue("#FFFFFF");
        await press("ArrowDown");
        expect(".o_hex_input").toHaveValue("#E6E6E6");
    });

    test("click on hue slider sets implicit focus on it", async () => {
        await setupEditor(
            `<p>
                <font style="color: rgb(0, 255, 0);">[test]</font>
            </p>`
        );
        await expandToolbar();
        await click(".o-we-toolbar .o-select-color-foreground");
        await animationFrame();
        await contains('.o_font_color_selector button:contains("Custom")').click();
        await contains(".o_font_color_selector .o_color_slider").click();
        await press("Tab");
        expect(getActiveElement()).toBe(queryFirst(".o_font_color_selector .o_opacity_pointer"));
        await contains(".o_font_color_selector .o_color_slider").click();
        expect(".o_hex_input").not.toHaveValue("#00FF00");
        await press("Home");
        expect(".o_hex_input").toHaveValue("#FF0000");
    });

    test("click on opacity slider sets implicit focus on it", async () => {
        await setupEditor(
            `<p>
                <font style="color: rgb(255, 0, 0);">[test]</font>
            </p>`
        );
        await expandToolbar();
        await click(".o-we-toolbar .o-select-color-foreground");
        await animationFrame();
        await contains('.o_font_color_selector button:contains("Custom")').click();
        const opacityPointer = queryOne(".o_opacity_pointer");
        expect(opacityPointer.ariaValueNow).toBe("100.00");
        await contains(".o_font_color_selector .o_opacity_slider").click();
        await press("Tab");
        expect(getActiveElement()).toBe(queryFirst(".o_font_color_selector .o_hex_input"));
        await contains(".o_font_color_selector .o_opacity_slider").click();
        expect(opacityPointer.ariaValueNow).not.toBe("100.00");
        const opacityValue = opacityPointer.ariaValueNow;
        await press("ArrowDown");
        expect(opacityPointer.ariaValueNow).not.toBe(opacityValue);
    });
});

describe.tags("desktop");
describe("color preview", () => {
    test("preview color should work and be reverted", async () => {
        await setupEditor("<p>[test]</p>");

        await expandToolbar();
        expect(".o_font_color_selector").toHaveCount(0);
        await click(".o-we-toolbar .o-select-color-foreground");
        await animationFrame();
        await hover(queryOne("button[data-color='o-color-1']"));
        await animationFrame();
        expect("font").toHaveCount(1);
        expect("font").toHaveClass("text-o-color-1");
        await hover(queryOne(".o-we-toolbar .o-select-color-foreground"));
        await animationFrame();
        expect("font").toHaveCount(0);
    });

    test("preview color and close dropdown should revert the preview", async () => {
        await setupEditor("<p>[test]</p>");

        await expandToolbar();
        expect(".o_font_color_selector").toHaveCount(0);
        await click(".o-we-toolbar .o-select-color-foreground");
        await animationFrame();
        await hover(queryOne("button[data-color='o-color-1']"));
        await animationFrame();
        expect("font").toHaveCount(1);
        expect("font").toHaveClass("text-o-color-1");
        await press("escape");
        await animationFrame();
        expect("font").toHaveCount(0);
    });

    test("preview color and then apply works with undo/redo", async () => {
        const { editor } = await setupEditor("<p>[test]</p>");

        await expandToolbar();
        expect(".o_font_color_selector").toHaveCount(0);
        await click(".o-we-toolbar .o-select-color-foreground");
        await animationFrame();
        await hover(queryOne("button[data-color='o-color-1']"));
        await animationFrame();
        expect("font").toHaveCount(1);
        expect("font").toHaveClass("text-o-color-1");
        await hover(queryOne("button[data-color='o-color-2']"));
        await animationFrame();
        expect("font").toHaveCount(1);
        expect("font").toHaveClass("text-o-color-2");
        await click("button[data-color='o-color-2']");
        await animationFrame();
        expect("font").toHaveCount(1);
        expect("font").toHaveClass("text-o-color-2");
        await animationFrame();
        execCommand(editor, "historyUndo");
        expect("font").toHaveCount(0);
        execCommand(editor, "historyRedo");
        expect("font").toHaveCount(1);
        expect("font").toHaveClass("text-o-color-2");
    });

    test("preview color are not restored when undo", async () => {
        const { editor } = await setupEditor("<p>[test]</p>");

        await expandToolbar();
        expect(".o_font_color_selector").toHaveCount(0);
        await click(".o-we-toolbar .o-select-color-foreground");
        await animationFrame();
        await hover(queryOne("button[data-color='o-color-1']"));
        await animationFrame();
        expect("font").toHaveCount(1);
        expect("font").toHaveClass("text-o-color-1");
        await hover(queryOne("button[data-color='o-color-2']"));
        await animationFrame();
        expect("font").toHaveCount(1);
        expect("font").toHaveClass("text-o-color-2");
        await press("escape");
        await animationFrame();
        expect("font").toHaveCount(0);
        execCommand(editor, "historyUndo");
        expect("font").toHaveCount(0);
    });

    test("should preview color in table on hover in solid tab", async () => {
        const defaultTextColor = "color: rgb(1, 10, 100);";
        const styleContent = `* {${defaultTextColor}}`;
        const { el } = await setupEditor(
            `
            <table class="table table-bordered o_table">
                <tbody>
                    <tr>
                        <td>
                            <p>[<br></p>
                        </td>
                    </tr>
                    <tr>
                        <td>
                            <p>]<br></p>
                        </td>
                    </tr>
                </tbody>
            </table>
        `,
            { styleContent }
        );
        await expandToolbar();
        await animationFrame();
        await click(".o-select-color-background");
        await animationFrame();
        // Hover a color
        await hover(queryOne("button[data-color='#CE0000']"));
        expect(getContent(el)).toBe(`
            <p data-selection-placeholder=""><br></p><table class="table table-bordered o_table o_selected_table">
                <tbody>
                    <tr>
                        <td class="o_selected_td o_selected_td_bg_color_preview" style="background-color: rgba(206, 0, 0, 0.6); ${defaultTextColor}">
                            <p>[<br></p>
                        </td>
                    </tr>
                    <tr>
                        <td class="o_selected_td o_selected_td_bg_color_preview" style="background-color: rgba(206, 0, 0, 0.6); ${defaultTextColor}">
                            <p>]<br></p>
                        </td>
                    </tr>
                </tbody>
            </table><p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>
        `);
        // Hover out
        await hover(queryOne(".o-we-toolbar .o-select-color-foreground"));
        await animationFrame();
        expect(getContent(el)).toBe(`
            <p data-selection-placeholder=""><br></p><table class="table table-bordered o_table o_selected_table">
                <tbody>
                    <tr>
                        <td class="o_selected_td">
                            <p>[<br></p>
                        </td>
                    </tr>
                    <tr>
                        <td class="o_selected_td">
                            <p>]<br></p>
                        </td>
                    </tr>
                </tbody>
            </table><p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>
        `);
        await expectElementCount(".o-we-toolbar", 1);
    });

    test("should preview color in table on hover in custom tab", async () => {
        const defaultTextColor = "color: rgb(1, 10, 100);";
        const styleContent = `* {${defaultTextColor}}`;
        const { el } = await setupEditor(
            `
            <table class="table table-bordered o_table">
                <tbody>
                    <tr>
                        <td>
                            <p>[<br></p>
                        </td>
                    </tr>
                    <tr>
                        <td>
                            <p><br>]</p>
                        </td>
                    </tr>
                </tbody>
            </table>
        `,
            { styleContent }
        );
        await expandToolbar();
        await animationFrame();
        await click(".o-select-color-background");
        await animationFrame();
        await click(".btn:contains('Custom')");
        await animationFrame();
        // Hover a color
        await hover(queryOne("button[data-color='black']"));
        expect(getContent(el)).toBe(`
            <p data-selection-placeholder=""><br></p><table class="table table-bordered o_table o_selected_table">
                <tbody>
                    <tr>
                        <td class="o_selected_td o_selected_td_bg_color_preview bg-black" style="${defaultTextColor}">
                            <p>[<br></p>
                        </td>
                    </tr>
                    <tr>
                        <td class="o_selected_td o_selected_td_bg_color_preview bg-black" style="${defaultTextColor}">
                            <p>]<br></p>
                        </td>
                    </tr>
                </tbody>
            </table><p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>
        `);
        // Hover out
        await hover(queryOne(".o-we-toolbar .o-select-color-foreground"));
        await animationFrame();
        expect(getContent(el)).toBe(`
            <p data-selection-placeholder=""><br></p><table class="table table-bordered o_table o_selected_table">
                <tbody>
                    <tr>
                        <td class="o_selected_td">
                            <p>[<br></p>
                        </td>
                    </tr>
                    <tr>
                        <td class="o_selected_td">
                            <p>]<br></p>
                        </td>
                    </tr>
                </tbody>
            </table><p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>
        `);
        await expectElementCount(".o-we-toolbar", 1);
    });

    test("should preview selected text color when tabbing", async () => {
        await setupEditor(
            `<p>
                This is a <font style="color: rgb(255, 0, 0);">[test]</font>.
            </p>`
        );

        await expandToolbar();
        await animationFrame();
        expect("i.fa-font").toHaveStyle({ borderBottomColor: "rgb(255, 0, 0)" });
        await click(".o-select-color-foreground");
        await animationFrame();
        await press("Tab"); // Tab to Custom
        await animationFrame();
        await press("Tab"); // Tab to Gradient
        await animationFrame();
        await press("Tab"); // Tab to Trash
        await animationFrame();
        expect(queryAll("font")).toHaveLength(0); // The color was deleted
        await press("Tab"); // Tab to 1st color
        await animationFrame();
        expect("font").toHaveStyle({ color: "rgb(113, 75, 103)" });
    });

    test("should preview when changing custom color", async () => {
        await setupEditor(`<p>This is a [test].</p>`);

        await expandToolbar();
        await animationFrame();
        await click(".o-select-color-foreground");
        await animationFrame();
        await click(".btn:contains('Custom')");
        await animationFrame();
        await contains(".o_font_color_selector .o_color_pick_area").click();
        expect("p font").toHaveAttribute("style");
        await press("Escape"); // Close tab and cancel preview.
        await animationFrame();
        expect(queryAll("font")).toHaveLength(0); // The color was deleted
    });

    test("should show the custom color preview in a color button", async () => {
        await setupEditor(`<p>This is a [test].</p>`);

        await expandToolbar();
        await animationFrame();
        await click(".o-select-color-foreground");
        await animationFrame();
        await click(".btn:contains('Custom')");
        await animationFrame();
        const colorBtnsLength =
            queryFirst(".o_colorpicker_section").querySelectorAll(".o_color_button").length;
        await contains(".o_font_color_selector .o_color_pick_area").click();
        await animationFrame();
        expect("p font").toHaveAttribute("style");
        const color = queryOne("p font").style.color;
        const hexColor = queryOne(".o_hex_input").value;
        expect(`.o_color_button[data-color='${hexColor}']`).toBeDisplayed();
        expect(`.o_color_button[data-color='${hexColor}']`).toHaveStyle({ backgroundColor: color });
        expect(
            queryFirst(".o_colorpicker_section").querySelectorAll(".o_color_button")
        ).toHaveLength(colorBtnsLength + 1);
    });

    test("should not modify the custom color preview button by hovering another color button", async () => {
        await setupEditor(`<p>This is a [test].</p>`);

        await expandToolbar();
        await animationFrame();
        await click(".o-select-color-foreground");
        await animationFrame();
        await click(".btn:contains('Custom')");
        await animationFrame();

        // 1. Hover a color button before modifying the custom color: should not
        // display the preview button.
        const colorBtnsLength =
            queryFirst(".o_colorpicker_section").querySelectorAll(".o_color_button").length;
        await contains(".o_color_button[data-color='black']").hover();
        await animationFrame();
        expect(
            queryFirst(".o_colorpicker_section").querySelectorAll(".o_color_button")
        ).toHaveLength(colorBtnsLength);

        // 2. Update custom color: should show the preview button with the
        // selected value.
        await contains(".o_font_color_selector .o_color_pick_area").click();
        await animationFrame();
        expect("p font").toHaveAttribute("style");
        const color = queryOne("p font").style.color;
        const hexColor = queryOne(".o_hex_input").value;
        expect(`.o_color_button[data-color='${hexColor}']`).toBeDisplayed();
        expect(`.o_color_button[data-color='${hexColor}']`).toHaveStyle({ backgroundColor: color });

        // 3. Hover a color button: should not impact the preview button.
        await contains(".o_color_button[data-color='black']").hover();
        await animationFrame();
        expect(`.o_color_button[data-color='${hexColor}']`).toHaveStyle({ backgroundColor: color });
    });

    test("should remove the custom color preview after switching tabs", async () => {
        await setupEditor(`<p>This is a [test].</p>`);

        await expandToolbar();
        await animationFrame();
        await click(".o-select-color-foreground");
        await animationFrame();
        await click(".btn:contains('Custom')");
        await animationFrame();
        await contains(".o_font_color_selector .o_color_pick_area").click();
        await animationFrame();
        expect("p font").toHaveAttribute("style");
        const color = queryOne("p font").style.color;
        const hexColor = queryOne(".o_hex_input").value;
        expect(`.o_color_button[data-color='${hexColor}']`).toBeDisplayed();
        expect(`.o_color_button[data-color='${hexColor}']`).toHaveStyle({ backgroundColor: color });
        await contains(".btn:contains('Gradient')").click();
        await animationFrame();
        await contains(".btn:contains('Custom')").click();
        await animationFrame();
        expect(queryAll(`.o_color_button[data-color='${hexColor}']`)).toHaveLength(0);
    });

    test("should apply custom color when clicking outside the popover", async () => {
        await setupEditor(`<p>This is a [test].</p>`);

        await expandToolbar();
        await animationFrame();
        await click(".o-select-color-foreground");
        await animationFrame();
        await click(".btn:contains('Custom')");
        await animationFrame();
        await contains(".o_font_color_selector .o_color_pick_area").click();
        expect("p font").toHaveAttribute("style");
        const color = queryOne("p font").style.color;
        await click("p");
        await animationFrame();
        expect("p font").toHaveStyle({ color });
    });

    test("should apply custom color when pressing Enter", async () => {
        await setupEditor(`<p>This is a [test].</p>`);

        await expandToolbar();
        await animationFrame();
        await click(".o-select-color-foreground");
        await animationFrame();
        await click(".btn:contains('Custom')");
        await animationFrame();
        await contains(".o_font_color_selector .o_color_pick_area").click();
        expect("p font").toHaveAttribute("style");
        const color = queryOne("p font").style.color;
        await press("Enter");
        await animationFrame();
        expect("p font").toHaveStyle({ color });
    });

    test("should preview the custom color after hovering out of color swatch", async () => {
        await setupEditor(`<p>This is a [test].</p>`);

        await expandToolbar();
        await animationFrame();
        await click(".o-select-color-foreground");
        await animationFrame();
        await click(".btn:contains('Custom')");
        await animationFrame();
        await contains(".o_font_color_selector .o_color_pick_area").click();
        await animationFrame();
        expect("p font").toHaveAttribute("style");
        const color = queryOne("p font").style.color;
        await contains(".o_colorpicker_section .o_color_button[data-color='800']").hover();
        await animationFrame();
        expect("p font").not.toHaveAttribute("style");
        expect("p font").toHaveClass("text-800");
        await contains(".btn:contains('Custom')").hover();
        await animationFrame();
        expect("p font").toHaveStyle({ color });
        expect("p font").not.toHaveAttribute("class");
        await press("Escape"); // Close tab and cancel preview.
        await animationFrame();
        expect(queryAll("font")).toHaveLength(0); // The color was deleted
    });

    test("should not preview the custom color if it was not modified first", async () => {
        await setupEditor(`
            <p>This is a <font class="text-gradient" style="background-image: linear-gradient(135deg, rgb(47, 128, 237) 0%, rgb(178, 255, 218) 100%);">[test]</font>.</p>
        `);

        await expandToolbar();
        await animationFrame();
        const gradient = queryOne("p font").style.backgroundImage;
        await click(".o-select-color-foreground");
        await animationFrame();
        await click(".btn:contains('Custom')");
        await animationFrame();
        await contains(".btn[title='Reset']").hover();
        await animationFrame();
        expect(queryAll("font")).toHaveLength(0);
        await hover("p");
        await animationFrame();
        expect(".o_hex_input").toHaveValue("#FF0000"); // Should not have any impact.
        // The value applied is still the gradient, not the custom color.
        expect("p font").toHaveStyle({ backgroundImage: gradient });
    });

    test("should not preview the custom color if it is not the active tab", async () => {
        await setupEditor(`<p>This is a [test].</p>`);

        await expandToolbar();
        await animationFrame();
        await click(".o-select-color-foreground");
        await animationFrame();
        await click(".btn:contains('Custom')");
        await animationFrame();
        await contains(".o_font_color_selector .o_color_pick_area").click();
        await animationFrame();
        expect("p font").toHaveAttribute("style");
        const color = queryOne("p font").style.color;
        await click(".btn:contains('Gradient')");
        await animationFrame();
        await contains(".o_gradient_color_button").hover();
        await animationFrame();
        expect("p font").not.toHaveStyle({ color });
        expect("p font").toHaveClass("text-gradient");
        await hover(".btn:contains('Gradient')");
        await animationFrame();
        expect(queryAll("font")).toHaveLength(0); // The color was deleted
    });

    test("should not apply the custom color when confirming another tab's color", async () => {
        await setupEditor(`<p>This is a [test].</p>`);

        await expandToolbar();
        await animationFrame();
        await click(".o-select-color-foreground");
        await animationFrame();
        await click(".btn:contains('Custom')");
        await animationFrame();
        await contains(".o_font_color_selector .o_color_pick_area").click();
        await animationFrame();
        expect("p font").toHaveAttribute("style");
        const customColor = queryOne("p font").style.color;
        await click(".btn:contains('Solid')");
        await animationFrame();
        await contains(".o_color_button[data-color='#FF00FF']").click();
        await animationFrame();
        expect("p font").not.toHaveStyle({ color: customColor });
        expect("p font").toHaveStyle({ color: "rgb(255, 0, 255)" });
    });

    test("should preview when changing the gradient", async () => {
        await setupEditor(`<p>This is a [test].</p>`);

        await expandToolbar();
        await animationFrame();
        await click(".o-select-color-foreground");
        await contains(".btn:contains('Gradient')").click();
        await contains(".o_custom_gradient_button").click(); // Click applies the default gradient.
        const initialGradient = queryOne(".o_custom_gradient_button").style.backgroundImage;
        await contains(".o_font_color_selector .o_color_pick_area").click();
        await animationFrame();
        expect(".o_custom_gradient_button").not.toHaveStyle({ backgroundImage: initialGradient });
        const gradient1 = queryOne(".o_custom_gradient_button").style.backgroundImage;
        await click("input[type='range'][name$='color 2']");
        await animationFrame();
        await contains(".o_font_color_selector .o_color_slider").click();
        await animationFrame();
        expect(".o_custom_gradient_button").not.toHaveStyle({ backgroundImage: initialGradient });
        expect(".o_custom_gradient_button").not.toHaveStyle({ backgroundImage: gradient1 });
        await press("Escape"); // Close tab and cancel preview.
        await animationFrame();
        expect("p font").toHaveStyle({ backgroundImage: initialGradient });
    });
});
