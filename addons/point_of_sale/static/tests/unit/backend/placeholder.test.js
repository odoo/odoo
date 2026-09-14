import "@point_of_sale/backend/many2many_placeholder_list_view/many2many_placeholder_list_view";

import { beforeEach, describe, expect, test } from "@odoo/hoot";
import {
    contains,
    defineModels,
    fields,
    models,
    mountView,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { user } from "@web/core/user";

for (const preset of ["desktop", "mobile"]) {
    describe(preset, () => {
        describe.current.tags(preset);
        beforeEach(() => patchWithCleanup(user, { hasGroup: async () => false }));

        class Bill extends models.Model {
            name = fields.Char();
            config_ids = fields.Many2many({ relation: "config" });
            _records = [{ id: 1, name: "Bill", config_ids: [] }];
        }
        class Config extends models.Model {
            name = fields.Char();
            _records = [{ id: 1, name: "Shop" }];
        }
        defineModels([Bill, Config]);

        test("empty readonly tags show the placeholder, editing uses the input placeholder", async () => {
            await mountView({
                type: "list",
                resModel: "bill",
                arch: `<list editable="bottom"><field name="name"/><field name="config_ids" widget="many2many_tags_placeholder_list_view" placeholder="All shops"/></list>`,
            });
            expect(".o_field_tags .opacity-50").toHaveText("All shops");
            await contains(".o_data_cell[name='config_ids']").click();
            expect(".o_field_tags .opacity-50").toHaveCount(0);
            expect(".o_field_tags input").toHaveAttribute("placeholder", "All shops");
        });

        test("populated tags do not show the empty placeholder", async () => {
            Bill._records[0].config_ids = [1];
            await mountView({
                type: "list",
                resModel: "bill",
                arch: `<list><field name="config_ids" widget="many2many_tags_placeholder_list_view" placeholder="All shops"/></list>`,
            });
            expect(".o_tag").toHaveText("Shop");
            expect(".o_field_tags .opacity-50").toHaveCount(0);
        });
    });
}
