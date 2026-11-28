import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-dom";
import { contains, getService, onRpc, serverState } from "@web/../tests/web_test_helpers";
import { cookie } from "@web/core/browser/cookie";
import { FavoriteColorsPlugin } from "@html_editor/components/color_picker/favorite_colors_plugin";
import { defineWebsiteModels, setupWebsiteBuilder } from "./website_helpers";

defineWebsiteModels();

test("the website builder offers the favorite colors of the company of the website", async () => {
    // The company of the website is allowed but not active.
    cookie.set("cids", "1");
    serverState.companies = [
        { ...serverState.companies[0], favorite_colors: ["#FF9C00"] },
        { id: 2, name: "Website company", currency_id: 1, favorite_colors: ["#00FFFF"] },
    ];
    onRpc("website", "web_search_read", () => ({
        length: 1,
        records: [{ id: 1, default_lang_id: { code: "en_US" }, company_id: 2 }],
    }));
    const { openBuilderSidebar } = await setupWebsiteBuilder("<section><p>Text</p></section>", {
        openEditor: false,
    });
    const favoriteColors = getService(FavoriteColorsPlugin);
    expect(favoriteColors.companyId).toBe(1);
    expect(favoriteColors.getColors()).toEqual(["#FF9C00"]);

    await openBuilderSidebar();
    expect(favoriteColors.companyId).toBe(2);
    expect(favoriteColors.getColors()).toEqual(["#00FFFF"]);

    // Leaving the website builder restores the active company.
    await contains(".o_hb_snippets_top_actions button[data-action='cancel']").click();
    await animationFrame();
    expect(".o_website_discard_save_buttons").toHaveCount(0);
    expect(favoriteColors.companyId).toBe(1);
    expect(favoriteColors.getColors()).toEqual(["#FF9C00"]);
});
