import { describe, expect, test } from "@odoo/hoot";
import { click, waitFor, queryOne, hover, press, waitUntil } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { setupEditor } from "./_helpers/editor";
import { getContent, setSelection } from "./_helpers/selection";
import { contains } from "@web/../tests/web_test_helpers";

test("can set foreground color", async () => {
    const { el } = await setupEditor("<p>[test]</p>");

    await waitFor(".o-we-toolbar");
    expect(".o_font_color_selector").toHaveCount(0);

    click(".o-select-color-foreground");
    await animationFrame();
    expect(".o_font_color_selector").toHaveCount(1);

    click(".o_color_button[data-color='#6BADDE']");
    await animationFrame();
    expect(".o-we-toolbar").toHaveCount(1); // toolbar still open
    expect(".o_font_color_selector").toHaveCount(0); // selector closed
    expect(getContent(el)).toBe(`<p><font style="color: rgb(107, 173, 222);">[test]</font></p>`);
});

test("can set background color", async () => {
    const { el } = await setupEditor("<p>[test]</p>");

    await waitFor(".o-we-toolbar");
    expect(".o_font_color_selector").toHaveCount(0);

    click(".o-select-color-background");
    await animationFrame();
    expect(".o_font_color_selector").toHaveCount(1);

    click(".o_color_button[data-color='#6BADDE']");
    await animationFrame();
    expect(".o-we-toolbar").toHaveCount(1); // toolbar still open
    expect(".o_font_color_selector").toHaveCount(0); // selector closed
    expect(getContent(el)).toBe(
        `<p><font style="background: rgb(107, 173, 222);">[test]</font></p>`
    );
});

test("can render and apply color theme", async () => {
    await setupEditor("<p>[test]</p>");

    await waitFor(".o-we-toolbar");
    expect(".o_font_color_selector").toHaveCount(0);
    click(".o-select-color-foreground");
    await animationFrame();
    expect(".o_font_color_selector").toHaveCount(1);
    expect("button[data-color='o-color-1']").toHaveCount(1);
    expect(queryOne("button[data-color='o-color-1']").style.backgroundColor).toBe(
        "var(--o-color-1)"
    );

    expect(".text-o-color-1").toHaveCount(0);
    click("button[data-color='o-color-1']");
    await waitFor(".text-o-color-1");
    expect(".text-o-color-1").toHaveCount(1);
});

test("can render and apply gradient color", async () => {
    await setupEditor("<p>[test]</p>");

    await waitFor(".o-we-toolbar");
    click(".o-select-color-foreground");
    await animationFrame();
    expect(queryOne("button[data-color='o-color-1']").style.backgroundColor).toBe(
        "var(--o-color-1)"
    );
    click(".btn:contains('Gradient')");
    await animationFrame();
    click(
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

test("custom colors used in the editor are shown in the colorpicker", async () => {
    await setupEditor(
        `<p>
            <font style="color: rgb(255, 0, 0);">[test]</font>
            <font style="color: rgb(0, 255, 0);">test</font>
        </p>`
    );
    await waitFor(".o-we-toolbar");
    expect(".o_font_color_selector").toHaveCount(0);
    click(".o-select-color-foreground");
    await animationFrame();
    click(".btn:contains('Custom')");
    await animationFrame();
    expect("button[data-color='rgb(255, 0, 0)']").toHaveCount(1);
    expect(queryOne("button[data-color='rgb(255, 0, 0)']").style.backgroundColor).toBe(
        "rgb(255, 0, 0)"
    );
    expect("button[data-color='rgb(0, 255, 0)']").toHaveCount(1);
    expect(queryOne("button[data-color='rgb(0, 255, 0)']").style.backgroundColor).toBe(
        "rgb(0, 255, 0)"
    );
});

test.tags("desktop")(
    "selected text color is shown in the toolbar and update when hovering",
    async () => {
        await setupEditor(
            `<p>
            <font style="color: rgb(255, 0, 0);">[test]</font>
        </p>`
        );

        await waitFor(".o-we-toolbar");
        expect(".o_font_color_selector").toHaveCount(0);
        await animationFrame();
        expect("i.fa-font").toHaveStyle({ borderBottomColor: "rgb(255, 0, 0)" });
        click(".o-select-color-foreground");
        await animationFrame();
        // Hover a color
        hover(queryOne("button[data-color='#FF00FF']"));
        await animationFrame();
        expect("i.fa-font").toHaveStyle({ borderBottomColor: "rgb(255, 0, 255)" });
        // Hover out
        hover(queryOne(".o-select-color-foreground"));
        await animationFrame();
        expect("i.fa-font").toHaveStyle({ borderBottomColor: "rgb(255, 0, 0)" });
    }
);

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
    click(".o-select-color-foreground");
    await animationFrame();
    click("button[data-color='#FF00FF']");
    await animationFrame();
    expect("i.fa-font").toHaveStyle({ borderBottomColor: "rgb(255, 0, 255)" });
});
test("selected text color is not shown in the toolbar after removeFormat", async () => {
    const { el } = await setupEditor(
        `<p>
            <font style="color: rgb(255, 0, 0);">t[es]t</font>
        </p>`
    );

    await waitFor(".o-we-toolbar");
    expect(".o_font_color_selector").toHaveCount(0);
    expect("i.fa-font").toHaveStyle({ borderBottomColor: "rgb(255, 0, 0)" });
    click(".btn.fa-eraser");
    await animationFrame();
    expect(getContent(el)).toBe(`<p>
            <font style="color: rgb(255, 0, 0);">t</font>[es]<font style="color: rgb(255, 0, 0);">t</font>
        </p>`);
    await animationFrame();
    // rgb(73, 80, 87) is aparently the default body color in the Hoot unit test
    // in community.
    expect("i.fa-font").toHaveStyle({ borderBottomColor: "rgb(73, 80, 87)" });
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
    click(".o-select-color-background");
    await animationFrame();
    click("button[data-color='#FF00FF']");
    await animationFrame();
    expect("i.fa-paint-brush").toHaveStyle({ borderBottomColor: "rgb(255, 0, 255)" });
});

test("clicking on button color parent does not crash", async () => {
    const { el } = await setupEditor("<p>[test]</p>");

    await waitFor(".o-we-toolbar");
    click(".o-select-color-foreground");
    await animationFrame();
    click(".o_colorpicker_section");
    await animationFrame();
    click(".o_color_button[data-color='#6BADDE']");
    await animationFrame();
    expect(getContent(el)).toBe(`<p><font style="color: rgb(107, 173, 222);">[test]</font></p>`);
});

test("gradient picker correctly shows the current selected gradient", async () => {
    await setupEditor(
        `<p><font style="background-image: linear-gradient(2deg, rgb(255, 204, 51) 10%, rgb(226, 51, 255) 90%);" class="text-gradient">[test]</font></p>`
    );
    await waitFor(".o-we-toolbar");
    expect(".o_font_color_selector").toHaveCount(0);
    click(".o-select-color-foreground");
    await animationFrame();
    click(".btn:contains('Gradient')");
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
    click(".o-select-color-foreground");
    await animationFrame();
    click(".btn:contains('Gradient')");
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
    click(".o-select-color-foreground");
    await animationFrame();
    click(".btn:contains('Gradient')");
    await animationFrame();
    expect("button.active:contains('Linear')").toHaveCount(1);
    await contains("input[name='angle'").click();
    expect("input[name='angle'").toHaveCount(1);
});

describe.tags("desktop")("color preview", () => {
    test("preview color should work and be reverted", async () => {
        await setupEditor("<p>[test]</p>");

        await waitFor(".o-we-toolbar");
        expect(".o_font_color_selector").toHaveCount(0);
        click(".o-select-color-foreground");
        await animationFrame();
        hover(queryOne("button[data-color='o-color-1']"));
        await animationFrame();
        expect("font").toHaveCount(1);
        expect("font").toHaveClass("text-o-color-1");
        hover(queryOne(".o-select-color-foreground"));
        await animationFrame();
        expect("font").toHaveCount(0);
    });

    test("preview color and close dropdown should revert the preview", async () => {
        await setupEditor("<p>[test]</p>");

        await waitFor(".o-we-toolbar");
        expect(".o_font_color_selector").toHaveCount(0);
        click(".o-select-color-foreground");
        await animationFrame();
        hover(queryOne("button[data-color='o-color-1']"));
        await animationFrame();
        expect("font").toHaveCount(1);
        expect("font").toHaveClass("text-o-color-1");
        press("escape");
        await animationFrame();
        expect("font").toHaveCount(0);
    });

    test("preview color and then apply works with undo/redo", async () => {
        const { editor } = await setupEditor("<p>[test]</p>");

        await waitFor(".o-we-toolbar");
        expect(".o_font_color_selector").toHaveCount(0);
        click(".o-select-color-foreground");
        await animationFrame();
        hover(queryOne("button[data-color='o-color-1']"));
        await animationFrame();
        expect("font").toHaveCount(1);
        expect("font").toHaveClass("text-o-color-1");
        hover(queryOne("button[data-color='o-color-2']"));
        await animationFrame();
        expect("font").toHaveCount(1);
        expect("font").toHaveClass("text-o-color-2");
        click("button[data-color='o-color-2']");
        await animationFrame();
        expect("font").toHaveCount(1);
        expect("font").toHaveClass("text-o-color-2");
        await animationFrame();
        editor.dispatch("HISTORY_UNDO");
        expect("font").toHaveCount(0);
        editor.dispatch("HISTORY_REDO");
        expect("font").toHaveCount(1);
        expect("font").toHaveClass("text-o-color-2");
    });

    test("preview color are not restored when undo", async () => {
        const { editor } = await setupEditor("<p>[test]</p>");

        await waitFor(".o-we-toolbar");
        expect(".o_font_color_selector").toHaveCount(0);
        click(".o-select-color-foreground");
        await animationFrame();
        hover(queryOne("button[data-color='o-color-1']"));
        await animationFrame();
        expect("font").toHaveCount(1);
        expect("font").toHaveClass("text-o-color-1");
        hover(queryOne("button[data-color='o-color-2']"));
        await animationFrame();
        expect("font").toHaveCount(1);
        expect("font").toHaveClass("text-o-color-2");
        press("escape");
        await animationFrame();
        expect("font").toHaveCount(0);
        editor.dispatch("HISTORY_UNDO");
        expect("font").toHaveCount(0);
    });
});
