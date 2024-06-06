import { test, expect, beforeEach } from "@odoo/hoot";
import { runAllTimers } from "@odoo/hoot-mock";
import { fields, models, defineModels, mountView } from "@web/../tests/web_test_helpers";

beforeEach(() => {
    const qweb = JSON.stringify([
        {
            exec_context: [],
            results: {
                archs: {
                    1: `<t name="Test1" t-name="test">
                <t t-call-assets="web.assets_tests"/>
            </t>`,
                },
                data: [
                    {
                        delay: 0.1,
                        directive: 't-call-assets="web.assets_tests"',
                        query: 9,
                        view_id: 1,
                        xpath: "/t/t",
                    },
                ],
            },
            stack: [],
            start: 42,
        },
    ]);

    class Custom extends models.Model {
        _name = "custom";

        qweb = fields.Text();

        _records = [{ qweb }];
    }

    class View extends models.Model {
        _name = "ir.ui.view";

        name = fields.Char();
        model = fields.Char();
        type = fields.Char();

        _records = [
            {
                id: 1,
                name: "formView",
                model: "custom",
                type: "form",
            },
        ];
    }

    defineModels([Custom, View]);
});

test("profiling qweb view field renders delay and query", async function (assert) {
    await mountView({
        resModel: "custom",
        type: "form",
        resId: 1,
        arch: `
        <form>
            <field name="qweb" widget="profiling_qweb_view"/>
        </form>`,
    });

    await runAllTimers();

    expect("[name='qweb'] .ace_gutter .ace_gutter-cell").toHaveCount(3);
    expect("[name='qweb'] .ace_gutter .ace_gutter-cell .o_info").toHaveCount(1);
    expect("[name='qweb'] .ace_gutter .ace_gutter-cell .o_info .o_delay").toHaveText("0.1");
    expect("[name='qweb'] .ace_gutter .ace_gutter-cell .o_info .o_query").toHaveText("9");
    expect("[name='qweb'] .o_select_view_profiling .o_delay").toHaveText("0.1 ms");
    expect("[name='qweb'] .o_select_view_profiling .o_query").toHaveText("9 query");
});
