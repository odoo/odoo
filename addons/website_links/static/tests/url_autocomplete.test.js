import { expect, test } from "@odoo/hoot";
import { advanceTime, queryAllTexts } from "@odoo/hoot-dom";
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

async function editAutocomplete(el, value) {
    await contains(el).edit(value, { confirm: false });
    await advanceTime(250);
}

function mockGetSuggestedLinks(callback = undefined) {
    onRpc("/website/get_suggested_links", ({ kwargs }) => {
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
