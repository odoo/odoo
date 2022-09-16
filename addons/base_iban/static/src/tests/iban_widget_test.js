/** @odoo-module **/
import { start, startServer } from '@mail/../tests/helpers/test_utils';
import { click, clickEdit, clickSave, editInput, getFixture } from "@web/../tests/helpers/utils";
import { DELAY } from "@base_iban/components/iban_widget/iban_widget";


QUnit.module('Fields', {}, function () {
    QUnit.module("IbanWidget");
    const [validIban, invalidIban] = ["BE12651194580992", "invalidIban!"];

    const openPreparedView = async (assert, validIbanList, startingAccNumber) => {
        const target = getFixture();
        const pyEnv = await startServer();
        const partnerId = pyEnv['res.partner'].create([
            {
                name: "Awesome partner",
                bank_ids: [
                    pyEnv['res.partner.bank'].create([{ acc_number: startingAccNumber }]),
                ],
            },
        ]);
        const views = {
            'res.partner,false,form':
                `<form>
                    <sheet>
                        <group>
                            <field name="name"/>
                        </group>
                        <field name="bank_ids">
                            <tree editable="bottom">
                                <field name="acc_number" widget="iban"/>
                            </tree>
                        </field>
                    </sheet>
                </form>`,
        };
        const { advanceTime, afterNextRender, openView } = await start({
            serverData: { views },
            hasTimeControl: true,
            mockRPC: function (route, args) {
                if (args.method === "check_iban") {
                    const iban = args.args[1].replace(/\s/g, '');
                    return Promise.resolve(iban === validIban);
                }
            },
        });
        await openView({
            res_id: partnerId,
            res_model: 'res.partner',
            views: [[false, 'form']],
        });
        return { target, advanceTime, afterNextRender };
    };

    QUnit.test('Iban Widget full flow', async assert => {
        const { target, advanceTime, afterNextRender } = await openPreparedView(assert, [validIban], "");

        assert.containsNone(target, ".o_iban", "Shouldn't display any validation icon while not editing");
        await clickEdit(target);
        assert.containsNone(target, ".o_iban",
            "Shouldn't display any validation icon while not editing a specific line");

        await click(target, "td.o_iban_cell");
        assert.containsNone(target, ".o_iban", "Shouldn't display any validation icon while iban is empty");

        await editInput(target, ".o_iban_cell .o_input", invalidIban);
        assert.containsNone(target, ".o_iban", "Shouldn't change its state of display before edition is finished");
        await afterNextRender(() => advanceTime(DELAY));
        assert.containsOnce(target, ".o_iban", "Should contain a validation icon 400ms after edition");
        assert.containsOnce(target, "i.fa.fa-times.o_iban_fail", "The validation icon should be the failed one");
        assert.containsNone(target, "i.fa.fa-check.o_iban", "The validation icon shouldn't be the successful one");

        await clickSave(target);
        assert.containsNone(target, ".o_iban", "Shouldn't display any validation while not editing");

        await clickEdit(target);
        assert.containsNone(target, ".o_iban",
            "Shouldn't display any validation icon while not editing a specific line");

        await click(target, "td.o_iban_cell");
        await afterNextRender(() => advanceTime(DELAY));
        assert.containsOnce(target, "i.fa.fa-times.o_iban_fail", "The validation icon should be present while clicking on an already filled IBAN");

        await editInput(target, ".o_iban_cell .o_input", validIban);
        assert.containsOnce(target, "i.fa.fa-times.o_iban_fail", "The validation icon shouldn't change during the edition");
        await afterNextRender(() => advanceTime(DELAY));
        assert.containsOnce(target, ".o_iban", "Should contain a validation icon 400ms after edition");
        assert.containsOnce(target, "i.fa.fa-check.o_iban", "The validation icon should be the successful one");
        assert.containsNone(target, "i.fa.fa-times.o_iban_fail", "The validation icon shouldn't be the failed one");

        await clickSave(target);
        assert.containsNone(target, ".o_iban", "Shouldn't display any validation while not editing");
    });
});
