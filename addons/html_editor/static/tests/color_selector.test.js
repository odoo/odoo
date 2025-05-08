import { describe, expect, test } from "@odoo/hoot";
import {
    click,
    waitFor,
    queryOne,
    hover,
    press,
    waitUntil,
    edit,
    queryAllValues,
    queryAll,
} from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { setupEditor } from "./_helpers/editor";
import { getContent, setSelection } from "./_helpers/selection";
import { contains } from "@web/../tests/web_test_helpers";
import { execCommand } from "./_helpers/userCommands";

test("can set foreground color", async () => {
    const { el } = await setupEditor("<p>[test]</p>");

    await waitFor(".o-we-toolbar");
    expect(".o_font_color_selector").toHaveCount(0);

    await click(".o-we-toolbar .o-select-color-foreground");
    await animationFrame();
    expect(".o_font_color_selector").toHaveCount(1);

    await click(".o_color_button[data-color='#6BADDE']");
    await animationFrame();
    await waitFor(".o-we-toolbar");
    expect(".o-we-toolbar").toHaveCount(1); // toolbar still open
    expect(".o_font_color_selector").toHaveCount(0); // selector closed
    expect(getContent(el)).toBe(`<p><font style="color: rgb(107, 173, 222);">[test]</font></p>`);
});

test("can set background color", async () => {
    const { el } = await setupEditor("<p>[test]</p>");

    await waitFor(".o-we-toolbar");
    expect(".o_font_color_selector").toHaveCount(0);

    await click(".o-select-color-background");
    await animationFrame();
    expect(".o_font_color_selector").toHaveCount(1);

    await click(".o_color_button[data-color='#6BADDE']");
    await animationFrame();
    await waitFor(".o-we-toolbar");
    expect(".o-we-toolbar").toHaveCount(1); // toolbar still open
    expect(".o_font_color_selector").toHaveCount(0); // selector closed
    expect(getContent(el)).toBe(
        `<p><font style="background-color: rgba(107, 173, 222, 0.6);">[test]</font></p>`
    );
});

test("should add opacity to custom background colors but not to theme colors", async () => {
    const { el } = await setupEditor("<p>[test]</p>");

    await waitFor(".o-we-toolbar");
    expect(".o_font_color_selector").toHaveCount(0);

    await contains(".o-select-color-background").click();
    expect(".o_font_color_selector").toHaveCount(1);

    await contains(".o_color_button[data-color='#FF0000']").click(); // Select a custom color.
    await waitFor(".o-we-toolbar");
    expect(".o-we-toolbar").toHaveCount(1);
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

test("can render and apply color theme", async () => {
    await setupEditor("<p>[test]</p>");

    await waitFor(".o-we-toolbar");
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

    await waitFor(".o-we-toolbar");
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
    await waitFor(".o-we-toolbar");
    expect(".o_font_color_selector").toHaveCount(0);
    await click(".o-we-toolbar .o-select-color-foreground");
    await animationFrame();
    await click(".btn:contains('Custom')");
    await animationFrame();
    expect(".o_hex_input").toHaveValue("#00FF00");
    expect(queryAllValues(".o_rgba_div input")).toEqual(["0", "255", "0", "100"]);
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
    await waitFor(".o-we-toolbar");
    expect(".o_font_color_selector").toHaveCount(0);
    await click(".o-we-toolbar .o-select-color-background");
    await animationFrame();
    await click(".btn:contains('Custom')");
    await animationFrame();
    expect(".o_hex_input").toHaveValue("#00FF00");
    expect(queryAllValues(".o_rgba_div input")).toEqual(["0", "255", "0", "100"]);
    expect(queryAll("button[data-color='#ff0000']")).toHaveCount(1);
    expect(queryOne("button[data-color='#ff0000']").style.backgroundColor).toBe("rgb(255, 0, 0)");
    expect(queryAll("button[data-color='#00ff00']")).toHaveCount(1);
    expect(queryOne("button[data-color='#00ff00']").style.backgroundColor).toBe("rgb(0, 255, 0)");
});

test("applied custom color should be shown in colorpicker after switching tab", async () => {
    const { el } = await setupEditor(
        '<p><font style="background-color: rgb(255, 0, 0);">[test]</font></p>'
    );
    await waitFor(".o-we-toolbar");
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
        '<p><font style="background-color: rgb(0, 255, 0);">[test]</font></p>'
    );
    await click(".btn:contains('Solid')");
    await animationFrame();
    await click(".btn:contains('Custom')");
    await animationFrame();
    expect(".o_hex_input").toHaveValue(newColor);
});

test("select hex color and apply it", async () => {
    const { el } = await setupEditor(`<p>[test]</p>`);
    await waitFor(".o-we-toolbar");
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
    expect(getContent(el)).toBe(`<p><font style="color: rgb(1, 126, 132);">[test]</font></p>`);

    await click(".odoo-editor-editable");
    await animationFrame();
    expect(".o_font_color_selector").toHaveCount(0);
    expect(getContent(el)).toBe(`<p><font style="color: rgb(1, 126, 132);">[test]</font></p>`);
});

test("always show the current custom color", async () => {
    const defaultTextColor = "rgb(1, 10, 100)";
    const styleContent = `* {color: ${defaultTextColor};}`;
    await setupEditor(`<p>[test]</p>`, { styleContent });
    await waitFor(".o-we-toolbar");
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
    await waitFor(".o-we-toolbar");
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
    await waitFor(".o-we-toolbar");
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

    await waitFor(".o-we-toolbar");
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

    await waitFor(".o-we-toolbar");
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

    await waitFor(".o-we-toolbar");
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

test("collapsed selection color is shown in the permanent toolbar", async () => {
    await setupEditor(`<font style="color: rgb(255, 0, 0);">t[]est</font>`, {
        props: { toolbar: true },
    });
    await animationFrame();
    expect("i.fa-font").toHaveStyle({ borderBottomColor: "rgb(255, 0, 0)" });
});

test("selected color is shown and updates when selection change", async () => {
    const { el } = await setupEditor(
        `<p><font style="color: rgb(255, 156, 0);">test1</font> <font style="color: rgb(150, 255, 0);">[test2]</font></p>`
    );
    await waitFor(".o-we-toolbar");
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

    await waitFor(".o-we-toolbar");
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

    await waitFor(".o-we-toolbar");
    await click(".o-we-toolbar .o-select-color-foreground");
    await animationFrame();
    await click(".o_colorpicker_section");
    await animationFrame();
    await click(".o_color_button[data-color='#6BADDE']");
    await animationFrame();
    expect(getContent(el)).toBe(`<p><font style="color: rgb(107, 173, 222);">[test]</font></p>`);
});

test("gradient picker correctly shows the current selected gradient", async () => {
    await setupEditor(
        `<p><font style="background-image: linear-gradient(2deg, rgb(255, 204, 51) 10%, rgb(226, 51, 255) 90%);" class="text-gradient">[test]</font></p>`
    );
    await waitFor(".o-we-toolbar");
    expect(".o_font_color_selector").toHaveCount(0);
    await click(".o-we-toolbar .o-select-color-foreground");
    await animationFrame();
    await click(".btn:contains('Gradient')");
    await animationFrame();
    expect("button.active:contains('Linear')").toHaveCount(1);
    expect("input[name='angle']").toHaveValue("2");
    expect("input[name='firstColorPercentage']").toHaveValue(10);
    expect("input[name='secondColorPercentage']").toHaveValue(90);
});

test("gradient picker does change the selector gradient color", async () => {
    await setupEditor(
        `<p><font style="background-image: linear-gradient(2deg, rgb(255, 204, 51) 10%, rgb(226, 51, 255) 90%);" class="text-gradient">[test]</font></p>`
    );
    await waitFor(".o-we-toolbar");
    expect(".o_font_color_selector").toHaveCount(0);
    await click(".o-we-toolbar .o-select-color-foreground");
    await animationFrame();
    await click(".btn:contains('Gradient')");
    await animationFrame();
    expect("button.active:contains('Linear')").toHaveCount(1);
    await contains("input[name='angle'").edit("10");
    await contains("input[name='firstColorPercentage']").edit(30);
    await contains("input[name='secondColorPercentage']").edit(50);
    expect("font.text-gradient").toHaveStyle({
        backgroundImage: "linear-gradient(10deg, rgb(255, 204, 51) 30%, rgb(226, 51, 255) 50%)",
    });
});

test("clicking on the angle input does not close the dropdown", async () => {
    await setupEditor(
        `<p><font style="background-image: linear-gradient(2deg, rgb(255, 204, 51) 10%, rgb(226, 51, 255) 90%);" class="text-gradient">[test]</font></p>`
    );
    await waitFor(".o-we-toolbar");
    expect(".o_font_color_selector").toHaveCount(0);
    await click(".o-we-toolbar .o-select-color-foreground");
    await animationFrame();
    await click(".btn:contains('Gradient')");
    await animationFrame();
    expect("button.active:contains('Linear')").toHaveCount(1);
    await contains("input[name='angle'").click();
    expect("input[name='angle'").toHaveCount(1);
});

test("should be able to select farthest-corner option in radial gradient", async () => {
    await setupEditor(`<p>a[bcd]e</p>`);
    await waitFor(".o-we-toolbar");
    await click(".o-we-toolbar .o-select-color-foreground");
    await animationFrame();
    expect(".btn:contains('Gradient')").toHaveCount(1);
    await click(".btn:contains('Gradient')");
    await animationFrame();
    expect("button:contains('Radial')").toHaveCount(1);
    await click(".btn:contains('Radial')");
    await animationFrame();
    expect("button[title='Extend to the farthest corner']").toHaveCount(1);
    await click("button[title='Extend to the farthest corner']");
    await animationFrame();
    expect("button[title='Extend to the farthest corner']").toHaveClass("active");
});

describe.tags("desktop");
describe("color preview", () => {
    test("preview color should work and be reverted", async () => {
        await setupEditor("<p>[test]</p>");

        await waitFor(".o-we-toolbar");
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

        await waitFor(".o-we-toolbar");
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

        await waitFor(".o-we-toolbar");
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

        await waitFor(".o-we-toolbar");
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
        await waitFor(".o-we-toolbar");
        await animationFrame();
        await click(".o-select-color-background");
        await animationFrame();
        // Hover a color
        await hover(queryOne("button[data-color='#CE0000']"));
        expect(getContent(el)).toBe(`
            <table class="table table-bordered o_table o_selected_table">
                <tbody>
                    <tr>
                        <td class="" style="background-color: rgb(206, 0, 0); ${defaultTextColor}">
                            <p>[<br></p>
                        </td>
                    </tr>
                    <tr>
                        <td class="" style="background-color: rgb(206, 0, 0); ${defaultTextColor}">
                            <p>]<br></p>
                        </td>
                    </tr>
                </tbody>
            </table>
        `);
        // Hover out
        await hover(queryOne(".o-we-toolbar .o-select-color-foreground"));
        await animationFrame();
        expect(getContent(el)).toBe(`
            <table class="table table-bordered o_table o_selected_table">
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
            </table>
        `);
        expect(".o-we-toolbar").toHaveCount(1); // toolbar still open
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
        await waitFor(".o-we-toolbar");
        await animationFrame();
        await click(".o-select-color-background");
        await animationFrame();
        await click(".btn:contains('Custom')");
        await animationFrame();
        // Hover a color
        await hover(queryOne("button[data-color='black']"));
        expect(getContent(el)).toBe(`
            <table class="table table-bordered o_table o_selected_table">
                <tbody>
                    <tr>
                        <td class="bg-black" style="${defaultTextColor}">
                            <p>[<br></p>
                        </td>
                    </tr>
                    <tr>
                        <td class="bg-black" style="${defaultTextColor}">
                            <p>]<br></p>
                        </td>
                    </tr>
                </tbody>
            </table>
        `);
        // Hover out
        await hover(queryOne(".o-we-toolbar .o-select-color-foreground"));
        await animationFrame();
        expect(getContent(el)).toBe(`
            <table class="table table-bordered o_table o_selected_table">
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
            </table>
        `);
        expect(".o-we-toolbar").toHaveCount(1); // toolbar still open
    });
});
