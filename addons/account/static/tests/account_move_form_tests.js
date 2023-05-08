/** @odoo-module **/
"use strict";

import { start, startServer } from "@mail/../tests/helpers/test_utils";
import { patchWithCleanup } from "@web/../tests/helpers/utils";
import { AccountMoveFormRenderer } from "@account/components/account_move_form/account_move_form";
import { accountMove as accountMoveService} from '@account/components/account_move_service/account_move_service';

QUnit.module("Views", {}, function (hooks) {
    QUnit.module('MoveFormView');

    QUnit.test("When I switch tabs, it saves", async (assert) => {
        const pyEnv = await startServer();
        const accountMove = pyEnv['account.move'].create([{ name: "move0" }]);

        const views = {
            'account.move,false,form':
                `<form js_class='account_move_form'>
                        <sheet>
                            <notebook>
                                <page id="invoice_tab" name="invoice_tab" string="Invoice Lines"></page>
                                <page id="aml_tab" string="Journal Items" name="aml_tab"></page>
                            </notebook>
                        </sheet>
                     </form>`,
        };
        const { click, openView } = await start({
            serverData: { views },
            services: {
                'account_move': accountMoveService,
            }
        });
        patchWithCleanup(AccountMoveFormRenderer.prototype, {
            saveBeforeTabChange() {
                this._super();
                assert.step("tab saved");
            },
        });
        await openView({
            res_id: accountMove,
            res_model: 'account.move',
            views: [[false, 'form']],
        });

        click('a[name="aml_tab"]');
        assert.verifySteps(["tab saved"],
            "When clicking on a tab, the saving method should be called and succeed");
    });

});
