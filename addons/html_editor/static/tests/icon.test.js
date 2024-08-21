import { expect, test } from "@odoo/hoot";
import { click, waitFor } from "@odoo/hoot-dom";
import { setupEditor } from "./_helpers/editor";
import { animationFrame } from "@odoo/hoot-mock";

test("icon toolbar is displayed", async () => {
    await setupEditor(`<p><span class="fa fa-glass">[]</span></p>`);
    await waitFor(".o-we-toolbar");
    expect(".btn-group[name='icon_size']").toHaveCount(1);
});

test("icon toolbar is displayed (2)", async () => {
    await setupEditor(`<p>abc<span class="fa fa-glass">[]</span>def</p>`);
    await waitFor(".o-we-toolbar");
    expect(".btn-group[name='icon_size']").toHaveCount(1);
});

test("Can resize an icon", async () => {
    await setupEditor(`<p><span class="fa fa-glass">[]</span></p>`);
    await waitFor(".o-we-toolbar");
    expect("span.fa-glass").toHaveCount(1);
    click("button[name='icon_size_2']");
    expect("span.fa-glass.fa-2x").toHaveCount(1);
    click("button[name='icon_size_3']");
    expect("span.fa-glass.fa-2x").toHaveCount(0);
    expect("span.fa-glass.fa-3x").toHaveCount(1);
    click("button[name='icon_size_4']");
    expect("span.fa-glass.fa-3x").toHaveCount(0);
    expect("span.fa-glass.fa-4x").toHaveCount(1);
    click("button[name='icon_size_5']");
    expect("span.fa-glass.fa-4x").toHaveCount(0);
    expect("span.fa-glass.fa-5x").toHaveCount(1);
    click("button[name='icon_size_1']");
    expect("span.fa-glass.fa-5x").toHaveCount(0);
});

test("Can spin an icon", async () => {
    await setupEditor(`<p><span class="fa fa-glass">[]</span></p>`);
    await waitFor(".o-we-toolbar");
    expect("span.fa-glass").toHaveCount(1);
    click("button[name='icon_spin']");
    expect("span.fa-glass").toHaveClass("fa-spin");
});

test("Can set icon color", async () => {
    await setupEditor(`<p><span class="fa fa-glass">[]</span></p>`);
    await waitFor(".o-we-toolbar");
    expect(".o_font_color_selector").toHaveCount(0);
    click(".o-select-color-foreground");
    await animationFrame();
    expect(".o_font_color_selector").toHaveCount(1);
    click(".o_color_button[data-color='#6BADDE']");
    await animationFrame();
    expect(".o-we-toolbar").toHaveCount(1); // toolbar still open
    expect(".o_font_color_selector").toHaveCount(0); // selector closed
    expect("span.fa-glass").toHaveStyle({ color: "rgb(107, 173, 222)" });
});
