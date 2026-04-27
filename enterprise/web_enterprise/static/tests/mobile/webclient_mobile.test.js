import { describe, expect, test } from "@odoo/hoot";
import { click, queryFirst } from "@odoo/hoot-dom";
import { animationFrame, mockMatchMedia } from "@odoo/hoot-mock";
import {
    defineActions,
    defineModels,
    fields,
    getService,
    models,
    mountWithCleanup,
} from "@web/../tests/web_test_helpers";

import { UserMenu } from "@web/webclient/user_menu/user_menu";
import { WebClientEnterprise } from "@web_enterprise/webclient/webclient";

class Partner extends models.Model {
    name = fields.Char();

    _records = [
        { id: 1, name: "First record" },
        { id: 2, name: "Second record" },
    ];
    _views = {
        form: `
            <form>
                <group>
                    <field name="name"/>
                </group>
            </form>
        `,
        kanban: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="name"/>
                    </t>
                </templates>
            </kanban>
        `,
        list: `<list><field name="name"/></list>`,
    };
}

defineModels([Partner]);

defineActions([
    {
        id: 1,
        xml_id: "action_1",
        name: "Partners Action 1",
        res_model: "partner",
        views: [[false, "kanban"]],
    },
    {
        id: 3,
        xml_id: "action_3",
        name: "Partners",
        res_model: "partner",
        views: [
            [false, "list"],
            [false, "kanban"],
            [false, "form"],
        ],
    },
]);

describe.current.tags("mobile");

test("scroll position is kept", async () => {
    // This test relies on the fact that the scrollable element in mobile
    // is view's root node.
    const firstRecord = Partner._records[0];
    delete firstRecord.id;
    Partner._records = [...Array(80)].map((_, i) => ({
        ...firstRecord,
        name: `Record ${i + 1}`,
    }));

    // force the html node to be scrollable element
    await mountWithCleanup(WebClientEnterprise);
    await animationFrame();

    // partners in list/kanban
    await getService("action").doAction(3);
    expect(".o_kanban_view").toHaveCount(1);

    queryFirst(".o_kanban_view").scrollTo(0, 123);
    await click(".o_kanban_record:eq(20)");
    await animationFrame();
    expect(".o_form_view").toHaveCount(1);
    expect(".o_kanban_view").toHaveCount(0);

    await click(".o_breadcrumb .o_back_button");
    await animationFrame();
    expect(".o_form_view").toHaveCount(0);
    expect(".o_kanban_view").toHaveCount(1);
});

test("Share URL item is not present in the user menu when screen is small", async () => {
    mockMatchMedia({ ["display-mode"]: "standalone" });

    await mountWithCleanup(UserMenu);

    expect(".o_user_menu").toHaveCount(1);
    queryFirst(".o_user_menu").classList.remove("d-none");

    await click(".o_user_menu button");
    await animationFrame();

    expect(".o_user_menu .dropdown-item").toHaveCount(0, {
        message: "share button is not visible",
    });
});
