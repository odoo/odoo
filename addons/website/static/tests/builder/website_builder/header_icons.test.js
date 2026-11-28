import { expect, test } from "@odoo/hoot";
import { click, dblclick, waitFor } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { redo, undo } from "@html_editor/../tests/_helpers/user_actions";
import { contains, onRpc } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

const cartIconHTML = `<i class="oi oi-stack o_not_editable" data-icon="shopping_cart" data-header-icon="cart" aria-hidden="true"
    data-oe-model="ir.ui.view" data-oe-id="42" data-oe-field="arch" data-oe-xpath="/t[1]/li[2]/a[1]/div[1]/t[1]/i[1]"></i>`;
const searchIconHTML = `<i class="oi" data-icon="search" data-header-icon="search"></i>`;

/**
 * A header shows its icons twice, in the desktop and the mobile navbar.
 */
function headerWithIcons(iconsHTML) {
    return `
        <header id="top" data-name="Header">
            <nav class="navbar">
                <div class="o_desktop">${iconsHTML}</div>
                <div class="o_mobile">${iconsHTML}</div>
            </nav>
        </header>
    `;
}
const headerHTML = headerWithIcons(`<a><div>${cartIconHTML}</div></a>`);

function stepSaveRpcs() {
    onRpc("ir.ui.view", "save", () => {
        expect.step("view save");
        return true;
    });
    onRpc("website", "set_header_icons", ({ args }) => {
        expect.step(args);
        return true;
    });
}

test("double clicking a header icon replaces its desktop and mobile copies, saved on the website", async () => {
    await setupWebsiteBuilder("", {
        headerContent: headerHTML.replaceAll("oi oi-stack", "oi oi-stack oi-filled"),
    });

    await dblclick(":iframe .o_desktop [data-header-icon=cart]");
    await waitFor(".modal .font-icons-icons");
    expect(".modal .nav-tabs .nav-link").toHaveCount(1);
    expect(".modal .nav-tabs .nav-link").toHaveText("Icons");

    await click(".modal .font-icons-icons [data-icon=favorite]:not(.oi-filled)");
    await waitFor(":iframe .o_mobile [data-header-icon=cart][data-icon=favorite]");
    expect(":iframe [data-header-icon=cart][data-icon=favorite]").toHaveCount(2);
    expect(":iframe [data-header-icon=cart].oi-filled").toHaveCount(0);

    stepSaveRpcs();
    await contains(".o_hb_snippets_top_actions button[data-action='save']").click();
    expect.verifySteps([[1, { cart: { icon: "favorite", filled: false } }]]);
});

test("clicking a header icon shows the double click hint, like other icons", async () => {
    await setupWebsiteBuilder("", { headerContent: headerHTML });

    await click(":iframe .o_desktop [data-header-icon=cart]");
    await animationFrame();
    expect("span:contains('Double-click to edit')").toHaveCount(1);
});

test("undoing and redoing a header icon replacement switch both copies of the icon", async () => {
    const { getEditor } = await setupWebsiteBuilder("", { headerContent: headerHTML });

    await dblclick(":iframe .o_desktop [data-header-icon=cart]");
    await waitFor(".modal .font-icons-icons");
    await click(".modal .font-icons-icons [data-icon=favorite]:not(.oi-filled)");
    await waitFor(":iframe .o_mobile [data-header-icon=cart][data-icon=favorite]");
    undo(getEditor());
    await animationFrame();
    expect(":iframe [data-header-icon=cart][data-icon=shopping_cart]").toHaveCount(2);

    redo(getEditor());
    await animationFrame();
    expect(":iframe [data-header-icon=cart][data-icon=favorite]").toHaveCount(2);

    stepSaveRpcs();
    await contains(".o_hb_snippets_top_actions button[data-action='save']").click();
    expect.verifySteps([[1, { cart: { icon: "favorite", filled: false } }]]);
});

test("a restricted editor cannot replace header icons", async () => {
    onRpc("res.users", "has_group", ({ args }) => args[1] !== "website.group_website_designer");
    await setupWebsiteBuilder("", { headerContent: headerHTML });

    await click(":iframe .o_desktop [data-header-icon=cart]");
    await animationFrame();
    expect("span:contains('Double-click to edit')").toHaveCount(0);

    await dblclick(":iframe .o_desktop [data-header-icon=cart]");
    await animationFrame();
    expect(".modal").toHaveCount(0);
});

test("the header panel has a Replace row for each icon in the header only, which replaces it", async () => {
    await setupWebsiteBuilder("", { headerContent: headerWithIcons(searchIconHTML) });
    await contains(":iframe #wrapwrap > header").click();
    await waitFor("[data-label='Search Icon']");
    expect("[data-action-id='replaceHeaderIcon']").toHaveCount(1);
    expect("[data-label='Language Icon']").toHaveCount(0);

    await contains("[data-label='Search Icon'] [data-action-id='replaceHeaderIcon']").click();
    await waitFor(".modal .font-icons-icons");
    await click(".modal .font-icons-icons .oi-filled[data-icon=favorite]");
    await waitFor(":iframe .o_mobile [data-header-icon=search][data-icon=favorite]");
    expect(":iframe [data-header-icon=search][data-icon=favorite].oi-filled").toHaveCount(2);
});
