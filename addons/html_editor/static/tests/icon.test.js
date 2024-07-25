import { expect, test } from "@odoo/hoot";
import { click, waitFor } from "@odoo/hoot-dom";
import { setupEditor } from "./_helpers/editor";

test("icon toolbar is displayed", async () => {
    await setupEditor(`<p><span class="fa fa-glass">[]</span></p>`);
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
