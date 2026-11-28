import { expect, mockUserAgent, test } from "@odoo/hoot";
import { animationFrame, click, press, queryOne } from "@odoo/hoot-dom";
import {
    getService,
    makeTestApp,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
    serverState,
} from "@web/../tests/web_test_helpers";
import { cookie } from "@web/core/browser/cookie";
import { user } from "@web/core/user";
import { ColorPicker } from "@html_editor/components/color_picker/color_picker";
import { FavoriteColorsPlugin } from "@html_editor/components/color_picker/favorite_colors_plugin";
import { setupEditor } from "./_helpers/editor";
import { getContent } from "./_helpers/selection";
import { expandToolbar } from "./_helpers/toolbar";

/**
 * @param {Object} [params]
 * @param {string} [params.selectedColor]
 * @param {Function} [params.applyColor]
 * @param {string[]} [params.favoriteColors] favorite colors of the company
 * @param {boolean} [params.isAdmin] whether the user can edit the company
 */
async function mountFavoriteTab({
    selectedColor = "",
    applyColor = () => {},
    favoriteColors = [],
    isAdmin = true,
} = {}) {
    serverState.companies = [{ ...serverState.companies[0], favorite_colors: favoriteColors }];
    // The user is rebuilt when the server state changes, patch it afterwards.
    patchWithCleanup(user, { isAdmin });
    onRpc("res.company", "add_favorite_color", ({ args }) => {
        expect.step(["add_favorite_color", args]);
        return [...favoriteColors, args[1]];
    });
    onRpc("res.company", "remove_favorite_color", ({ args }) => {
        expect.step(["remove_favorite_color", args]);
        return favoriteColors.filter((color) => color !== args[1]);
    });
    // Writing on a company reloads the web client.
    onRpc("res.company", "write", () => expect.step("write"));
    await mountWithCleanup(ColorPicker, {
        props: {
            state: {
                selectedColor,
                defaultTab: "favorite",
            },
            applyColor,
            enabledTabs: ["solid", "custom"],
        },
    });
}

test.tags("desktop");
test("favorite tab is always added and displayed with an icon", async () => {
    await mountFavoriteTab();
    expect(".o_font_color_selector .btn-tab").toHaveCount(3);
    expect("button.favorite-tab").toHaveClass("active");
    expect("button.favorite-tab").toHaveAttribute("title", "Company favorite colors");
    expect("button.favorite-tab .oi[data-icon='favorite']").toHaveAttribute("aria-hidden", "true");
    expect("button.favorite-tab").toHaveAttribute("aria-label", "Company favorite colors");
    expect("button.favorite-tab").toHaveText("");
    // Tabs without icon keep displaying their name.
    expect("button.solid-tab").toHaveText("Solid");
    expect("button.solid-tab").not.toHaveAttribute("title");
});

test.tags("mobile");
test("favorite tab is displayed with its name in the mobile dropdown", async () => {
    mockUserAgent("android");
    await mountFavoriteTab();
    await click(".o_font_color_selector .btn.border-dark");
    await animationFrame();
    expect(".o-dropdown-item:last-child").toHaveText("Company favorite colors");
    expect(".o-dropdown-item .oi[data-icon='favorite']").toHaveCount(0);
});

test("favorite tab starts with only the add button", async () => {
    await mountFavoriteTab();
    expect(".o_favorite_color").toHaveCount(0);
    expect(".o_favorite_color_add").toHaveCount(1);
    expect(".o_colorpicker_widget").toHaveCount(0);
});

test("favorite tab is hidden when there is nothing to choose nor the right to add", async () => {
    await mountFavoriteTab({ selectedColor: "#B5D6A5", isAdmin: false });
    expect(".o_favorite_color").toHaveCount(0);
    expect(".o_font_color_selector .favorite-tab").toHaveCount(0);
    // Fallback to the first enabled tab.
    expect(".o_font_color_selector .o_color_section").toHaveCount(1);
});

test("favorite colors can be used without the right to edit them", async () => {
    await mountFavoriteTab({
        isAdmin: false,
        favoriteColors: ["#FF9C00"],
        applyColor(color) {
            expect.step(color);
        },
    });
    expect(".o_favorite_color .o_color_button").toHaveCount(1);
    expect(".o_favorite_color_add").toHaveCount(0);
    expect(".o_favorite_color_remove").toHaveCount(0);
    await click(".o_favorite_color .o_color_button");
    expect.verifySteps(["#FF9C00"]);
});

test("favorite colors are named after their hexadecimal code", async () => {
    await mountFavoriteTab({ favoriteColors: ["#FF9C00"] });
    expect(".o_favorite_color .o_color_button").toHaveAttribute("aria-label", "#FF9C00");
    expect(".o_favorite_color .o_color_button").toHaveAttribute("data-tooltip", "#FF9C00");
    expect(".o_favorite_color .o_color_button").toHaveAttribute("data-tooltip-position", "bottom");
});

test("add a favorite color in a sub panel, starting from the current color", async () => {
    await mountFavoriteTab({ selectedColor: "#B5D6A5", favoriteColors: ["#FF9C00"] });
    await click(".o_favorite_color_add");
    await animationFrame();
    // The sub panel replaces the tabs, with a title and a back button.
    expect(".o_color_picker_sub_panel").toHaveCount(1);
    expect(".o_color_picker_sub_panel").toHaveText(/^Add a favorite color/);
    expect(".o_color_picker_sub_panel button[aria-label='Go back']").toBeFocused();
    expect(".btn-tab").not.toBeVisible();
    expect(".o_color_picker_favorite_tab").not.toBeVisible();
    expect(".o_color_picker_sub_panel .o_colorpicker_widget").toHaveCount(1);
    expect(".o_color_picker_sub_panel .btn-primary").toHaveText("Add");
    // The buttons must not submit a form the color picker would be in.
    expect(
        ".o_color_picker_sub_panel button:not(.o_colorpicker_widget button):not([type='button'])"
    ).toHaveCount(0);

    await click(".o_color_picker_sub_panel .btn-primary");
    await animationFrame();
    expect(".o_color_picker_sub_panel").toHaveCount(0);
    expect(".o_color_picker_favorite_tab").toBeVisible();
    // Keep the focus in the color picker, so that it stays open.
    expect(".o_favorite_color_add").toBeFocused();
    expect(".o_favorite_color .o_color_button").toHaveCount(2);
    // The new color is added just before the add button.
    expect(".o_favorite_color:nth-child(2) .o_color_button").toHaveAttribute(
        "data-color",
        "#B5D6A5"
    );
    expect(".o_favorite_color + .o_favorite_color_add").toHaveCount(1);
    expect.verifySteps([["add_favorite_color", [[1], "#B5D6A5"]]]);
    expect(getService(FavoriteColorsPlugin).getColors()).toEqual(["#FF9C00", "#B5D6A5"]);
});

test("adding a color already in the favorites notifies it instead", async () => {
    await mountFavoriteTab({ selectedColor: "#b5d6a5", favoriteColors: ["#B5D6A5"] });
    await click(".o_favorite_color_add");
    await animationFrame();
    await click(".o_color_picker_sub_panel .btn-primary");
    await animationFrame();
    expect(".o_favorite_color").toHaveCount(1);
    expect(".o_notification").toHaveCount(1);
    expect(".o_notification").toHaveText("This color is already in the favorite colors.");
    // The color can still be changed.
    expect(".o_color_picker_sub_panel .o_colorpicker_widget").toHaveCount(1);
    expect.verifySteps([]);
});

test("going back from the sub panel does not add the color", async () => {
    await mountFavoriteTab({ selectedColor: "#B5D6A5" });
    await click(".o_favorite_color_add");
    await animationFrame();
    await click(".o_color_picker_sub_panel button[aria-label='Go back']");
    await animationFrame();
    expect(".o_color_picker_sub_panel").toHaveCount(0);
    expect(".o_favorite_color_add").toBeFocused();
    expect(".o_favorite_color").toHaveCount(0);
    expect.verifySteps([]);
});

test("escape closes the sub panel, not the color picker", async () => {
    await mountFavoriteTab({ selectedColor: "#B5D6A5" });
    await click(".o_favorite_color_add");
    await animationFrame();
    await press("escape");
    await animationFrame();
    expect(".o_color_picker_sub_panel").toHaveCount(0);
    expect(".o_color_picker_favorite_tab").toBeVisible();
    expect(".o_favorite_color_add").toBeFocused();
    expect(".o_favorite_color").toHaveCount(0);
    expect.verifySteps([]);
});

test.tags("desktop");
test("escape closes the sub panel, then the color picker of the editor toolbar", async () => {
    onRpc("res.company", "add_favorite_color", () => []);
    const { el } = await setupEditor("<p>[test]</p>");
    await expandToolbar();
    await click(".o-we-toolbar .o-select-color-foreground");
    await animationFrame();
    await click("button.favorite-tab");
    await animationFrame();
    await click(".o_favorite_color_add");
    await animationFrame();
    await press("escape");
    await animationFrame();
    expect(".o_font_color_selector").toHaveCount(1);
    expect(".o_color_picker_sub_panel").toHaveCount(0);
    await press("escape");
    await animationFrame();
    expect(".o_font_color_selector").toHaveCount(0);
    expect(getContent(el)).toBe("<p>[test]</p>");
});

test("clicking a favorite color applies it", async () => {
    await mountFavoriteTab({
        favoriteColors: ["#FF9C00"],
        applyColor(color) {
            expect.step(color);
        },
    });
    await click(".o_favorite_color .o_color_button");
    expect.verifySteps(["#FF9C00"]);
});

test("remove a favorite color", async () => {
    await mountFavoriteTab({
        favoriteColors: ["#FF9C00", "#00FFFF"],
        applyColor(color) {
            expect.step(color);
        },
    });
    // The remove button only shows up on hover, or when a color is focused.
    expect(".o_favorite_color_remove").not.toBeVisible();
    queryOne(".o_favorite_color:first-child .o_color_button").focus();
    expect(".o_favorite_color:first-child .o_favorite_color_remove").toBeVisible();
    expect(".o_favorite_color:nth-child(2) .o_favorite_color_remove").not.toBeVisible();
    await click(".o_favorite_color:first-child .o_favorite_color_remove");
    await animationFrame();
    expect(".o_favorite_color_add").toBeFocused();
    expect(".o_favorite_color .o_color_button").toHaveCount(1);
    expect(".o_favorite_color .o_color_button").toHaveAttribute("data-color", "#00FFFF");
    // Removing a color does not apply anything.
    expect.verifySteps([["remove_favorite_color", [[1], "#FF9C00"]]]);
});

test("favorite colors are kept by company", async () => {
    serverState.companies = [
        { ...serverState.companies[0], favorite_colors: ["#FF9C00"] },
        { id: 2, name: "Other", currency_id: 1, favorite_colors: ["#00FFFF"] },
    ];
    onRpc("res.company", "add_favorite_color", ({ args }) => {
        expect.step(["add_favorite_color", args]);
        return ["#00FFFF", args[1]];
    });
    onRpc("res.company", "remove_favorite_color", ({ args }) => {
        expect.step(["remove_favorite_color", args]);
        return [];
    });
    await makeTestApp();
    const favoriteColors = getService(FavoriteColorsPlugin);
    // The active company is used by default.
    expect(favoriteColors.getColors()).toEqual(["#FF9C00"]);
    expect(favoriteColors.getColors(1)).toEqual(["#FF9C00"]);
    expect(favoriteColors.getColors(2)).toEqual(["#00FFFF"]);
    expect(favoriteColors.canEdit(2)).toBe(true);
    // A company which is not allowed to the user has no favorite colors.
    expect(favoriteColors.getColors(3)).toEqual([]);
    expect(favoriteColors.canEdit(3)).toBe(false);

    await favoriteColors.add("#b5d6a5", 2);
    expect(favoriteColors.getColors(2)).toEqual(["#00FFFF", "#B5D6A5"]);
    await favoriteColors.remove("#00FFFF", 2);
    expect(favoriteColors.getColors(2)).toEqual([]);
    expect(favoriteColors.getColors(1)).toEqual(["#FF9C00"]);
    expect.verifySteps([
        ["add_favorite_color", [[2], "#B5D6A5"]],
        ["remove_favorite_color", [[2], "#00FFFF"]],
    ]);
});

test("use the company related to what is being edited", async () => {
    // Company 2 is allowed but not active, company 3 is not allowed.
    cookie.set("cids", "1");
    serverState.companies = [
        { ...serverState.companies[0], favorite_colors: ["#FF9C00"] },
        { id: 2, name: "Other", currency_id: 1, favorite_colors: ["#00FFFF"] },
    ];
    onRpc("res.company", "add_favorite_color", ({ args }) => {
        expect.step(["add_favorite_color", args]);
        return ["#00FFFF", args[1]];
    });
    await makeTestApp();
    const favoriteColors = getService(FavoriteColorsPlugin);
    expect(favoriteColors.companyId).toBe(1);
    expect(favoriteColors.getColors()).toEqual(["#FF9C00"]);

    const restore = favoriteColors.useCompany(2);
    expect(favoriteColors.companyId).toBe(2);
    expect(favoriteColors.getColors()).toEqual(["#00FFFF"]);
    expect(favoriteColors.canEdit()).toBe(true);
    await favoriteColors.add("#B5D6A5");
    expect.verifySteps([["add_favorite_color", [[2], "#B5D6A5"]]]);

    restore();
    expect(favoriteColors.companyId).toBe(1);
    expect(favoriteColors.getColors()).toEqual(["#FF9C00"]);

    // The colors of a company which is not allowed are unknown: nothing changes.
    favoriteColors.useCompany(3);
    expect(favoriteColors.companyId).toBe(1);
});

test("favorite colors are not offered by public editors", async () => {
    // Public editors (forum, blog comments, portal chatter) run with the
    // frontend session, which has no company: even an administrator then
    // neither gets favorite colors nor the right to add some.
    patchWithCleanup(user, {
        allowedCompanies: [],
        get activeCompany() {
            return undefined;
        },
    });
    await mountWithCleanup(ColorPicker, {
        props: {
            state: {
                selectedColor: "",
                defaultTab: "favorite",
            },
            applyColor() {},
            enabledTabs: ["solid", "custom"],
        },
    });
    expect(user.isAdmin).toBe(true);
    expect(user.allowedCompanies).toEqual([]);
    expect(".o_font_color_selector .btn-tab").toHaveCount(2);
    expect(".o_font_color_selector .favorite-tab").toHaveCount(0);
    expect(".o_color_picker_favorite_tab").toHaveCount(0);
});
