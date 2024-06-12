/* @odoo-module */

import { accountMove as accountMoveService } from "@account/components/account_move_service/account_move_service";

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start } from "@mail/../tests/helpers/test_utils";

import { makeDeferred, triggerHotkey } from "@web/../tests/helpers/utils";
import { click, insertText } from "@web/../tests/utils";

QUnit.module("Views", {}, function () {
    QUnit.module("MoveFormView");

    QUnit.test("When I switch tabs, it saves", async (assert) => {
        const pyEnv = await startServer();
        const accountMove = pyEnv["account.move"].create([{ name: "move0" }]);

        const views = {
            "account.move,false,form": `<form js_class='account_move_form'>
                        <sheet>
                            <notebook>
                                <page id="invoice_tab" name="invoice_tab" string="Invoice Lines">
                                    <field name="name"/>
                                </page>
                                <page id="aml_tab" string="Journal Items" name="aml_tab"></page>
                            </notebook>
                        </sheet>
                     </form>`,
        };
        const def = makeDeferred();
        const { openFormView } = await start({
            serverData: { views },
            services: {
                account_move: accountMoveService,
            },
            async mockRPC(route) {
                if (route === "/web/dataset/call_kw/account.move/web_save") {
                    assert.step("tab saved");
                    def.resolve();
                }
            },
        });
        openFormView("account.move", accountMove);
        await insertText("[name='name'] input", "somebody save me!");
        triggerHotkey("Enter");

        await click('a[name="aml_tab"]');
        await def;
        assert.verifySteps(
            ["tab saved"],
            "When clicking on a tab, the saving method should be called and succeed"
        );
    });
});
