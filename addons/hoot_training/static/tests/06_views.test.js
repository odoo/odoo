import { expect, test } from "@odoo/hoot";
import { queryAllTexts } from "@odoo/hoot-dom";
import { defineModels, fields, models, mountView, onRpc } from "@web/../tests/web_test_helpers";

class Duck extends models.Model {
    _name = "duck";
    _records = [{ name: "Donald" }, { name: "Scrooge" }];

    name = fields.Char();

    _views = {
        form: /* xml */ `
            <form>
                <field name="display_name" />
            </form>
        `,
        list: /* xml */ `
            <list>
                <field name="display_name" />
            </list>
        `,
    };
}

defineModels([Duck]);

onRpc("has_group", () => true); // Needed by the list controller

/**
 * @hint `mountView()` ("@web/../tests/web_test_helpers") is more convenient
 * @hint typo in the name of the `Duck model definition
 * @hint declare a `name` field on `Duck` with `fields` ("@web/../tests/web_test_helpers")
 * @hint give `Duck` to `defineModels()` ("@web/../tests/web_test_helpers") to load it in the mock server
 */
test("form view works with ducks", async () => {
    await mountView({
        type: "form",
        resId: 1,
        resModel: "duck",
    });

    expect(".o_form_renderer").toHaveText("Donald");
});

/**
 * @hint `Duck._records` can directly be altered, no need to declare a whole new model from scratch
 * @hint `expect.step` in `onRpc()`
 */
test("list view works with ducks", async () => {
    Duck._records = [{ name: "Huey" }, { name: "Dewey" }, { name: "Louie" }];

    onRpc(({ method }) => expect.step(method));

    await mountView({
        type: "list",
        resModel: "duck",
    });

    expect(queryAllTexts(`[name=display_name]`)).toEqual(["Huey", "Dewey", "Louie"]);
    expect.verifySteps(["get_views", "web_search_read", "has_group"]);
});
