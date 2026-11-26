import { expect, test } from "@odoo/hoot";
import { animationFrame, click, queryAllTexts, runAllTimers } from "@odoo/hoot-dom";
import { mailModels } from "@mail/../tests/mail_test_helpers";
import {
    contains,
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
} from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";

class Partner extends models.Model {
    url = fields.Char();
}

defineModels({ ...mailModels, Partner });

function mockGetSuggestedLinks(callback = undefined) {
    onRpc("/website/get_suggested_links", () => {
        callback?.();
        return {
            matching_pages: [
                {
                    value: "/page1",
                    label: "/page1 (Page 1)",
                },
                {
                    value: "/page2",
                    label: "/page2 (Page 2)",
                },
            ],
            others: [
                {
                    title: "Last modified pages",
                    values: [
                        {
                            value: "/page3",
                            label: "/page3 (Page 3)",
                        },
                    ],
                },
                {
                    title: "Apps url",
                    values: [
                        {
                            value: "/app1",
                            label: "/app1 (App 1)",
                            icon: "app1_icon",
                        },
                    ],
                },
            ],
        };
    });
}

test("UrlAutoCompleteField in form view", async () => {
    mockGetSuggestedLinks(() => {
        expect.step("get_suggested_links");
    });
    await mountView({
        type: "form",
        resModel: "partner",
        // resId: 1,
        arch: `<form>
                   <field name="url" widget="url_autocomplete"/>
               </form>`,
    });

    expect(".o_field_url_autocomplete").toHaveCount(1);
    expect(".o_field_url_autocomplete .dropdown-menu").toHaveCount(0);

    // Check dropdown exist
    await contains(".o_field_url_autocomplete input").click();
    expect(".o_field_url_autocomplete .dropdown-menu").toHaveCount(1);
    expect(queryAllTexts(".o-autocomplete--dropdown-item")).toEqual([
        "/page1 (Page 1)",
        "/page2 (Page 2)",
        "Last modified pages",
        "/page3 (Page 3)",
        "Apps url",
        "/app1 (App 1)",
    ]);

    // Select dropdown item
    await contains(".o-autocomplete--dropdown-item:last").click();
    const expectedUrl = browser.location.origin + "/app1";
    expect(".o-autocomplete input").toHaveValue(expectedUrl);

    // Verify steps finally to be sure that rpc is called
    expect.verifySteps(["get_suggested_links"]);
});

test("UrlAutoCompleteField rejects malformed urls", async () => {
    onRpc("/website/get_suggested_links", () => ({ matching_pages: [], others: [] }));
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `<form>
                   <field name="url" widget="url_autocomplete"/>
               </form>`,
    });

    for (const invalidUrl of ["htps://odoo.com", "javascript:alert(1)", "odoo", "http://"]) {
        await contains(".o_field_url_autocomplete input").edit(invalidUrl, { confirm: "blur" });
        expect(".o_field_url_autocomplete").toHaveClass("o_field_invalid", {
            message: `"${invalidUrl}" should be invalid`,
        });
    }

    for (const validUrl of ["https://www.odoo.com/contactus", "odoo.com", "localhost:8069/shop"]) {
        await contains(".o_field_url_autocomplete input").edit(validUrl, { confirm: "blur" });
        expect(".o_field_url_autocomplete").not.toHaveClass("o_field_invalid", {
            message: `"${validUrl}" should be valid`,
        });
    }

    await contains(".o_field_url_autocomplete input").edit("/contactus", { confirm: "blur" });
    expect(".o_field_url_autocomplete input").toHaveValue(browser.location.origin + "/contactus");
});

test("UrlAutoCompleteField selects the first suggestion when clicking away", async () => {
    mockGetSuggestedLinks();
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `<form>
                   <field name="url" widget="url_autocomplete"/>
               </form>`,
    });

    await contains(".o_field_url_autocomplete input").edit("page", { confirm: false });
    await runAllTimers();
    expect(".o_field_url_autocomplete .dropdown-menu").toHaveCount(1);

    await click(".o_form_view");
    await animationFrame();
    expect(".o_field_url_autocomplete input").toHaveValue(browser.location.origin + "/page1");
    expect(".o_field_url_autocomplete").not.toHaveClass("o_field_invalid");
});

test("UrlAutoCompleteField saves the selected suggestion", async () => {
    Partner._records = [{ id: 1, url: false }];
    mockGetSuggestedLinks();
    onRpc("partner", "web_save", ({ args }) => {
        expect.step(args[1].url);
    });
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `<form>
                   <field name="url" widget="url_autocomplete"/>
               </form>`,
    });

    await contains(".o_field_url_autocomplete input").click();
    await contains(".o-autocomplete--dropdown-item:first").click();
    await contains(".o_form_button_save").click();
    expect.verifySteps([browser.location.origin + "/page1"]);
});
