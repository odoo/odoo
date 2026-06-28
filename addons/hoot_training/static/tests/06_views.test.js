import { expect, test } from "@odoo/hoot";
import { queryAllTexts } from "@odoo/hoot-dom";
import { models, mountWithCleanup, onRpc } from "@web/../tests/web_test_helpers";

import { View } from "@web/views/view";

class Duck extends models.Model {
    _name = "duck";
    _records = [{ name: "Donald" }, { name: "Scrooge" }];

    _views = {
        form: /* xml */ `
            <form>
                <field name="display_name" />
            </form>
        `,
    };
}

onRpc("has_group", () => true); // Needed by the list controller

/**
 * @hint `mountView()` ("@web/../tests/web_test_helpers") is more convenient
 * @hint typo in the name of the `Duck model definition
 * @hint declare a `name` field on `Duck` with `fields` ("@web/../tests/web_test_helpers")
 * @hint give `Duck` to `defineModels()` ("@web/../tests/web_test_helpers") to load it in the mock server
 */
test.todo("form view works with ducks", async () => {
    await mountWithCleanup(View, {
        props: {
            type: "form",
            resId: 1,
            resModel: "dcuk",
        },
    });

    expect(".o_form_renderer").toHaveText("Donald");
});

/**
 * @hint `Duck._records` can directly be altered, no need to declare a whole new model from scratch
 * @hint `expect.step` in `onRpc()`
 */
test.todo("list view works with ducks", async () => {
    class Duck extends models.Model {
        _name = "duck";
        _records = [{ name: "Huey" }, { name: "Dewey" }, { name: "Louie" }];
        _views = {
            list: /* xml */ `
                <list>
                    <field name="display_name" />
                </list>
            `,
        };
    }

    await mountWithCleanup(View, {
        props: {
            type: "list",
            resModel: "duck",
        },
    });

    expect(queryAllTexts(`[name=display_name]`)).toEqual(["Huey", "Dewey", "Louie"]);
    expect.verifySteps(["get_views", "web_search_read", "has_group"]);
});
