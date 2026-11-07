/* @odoo-module */

import { DELAY } from "@base_iban/components/iban_widget/iban_widget";
import { startServer } from "@bus/../tests/helpers/mock_python_environment";
import { start } from "@mail/../tests/helpers/test_utils";
import { click, contains, insertText } from "@web/../tests/utils";

QUnit.module("Fields", {}, function () {
    QUnit.module("IbanWidget");
    const [validIban, invalidIban] = ["BE12651194580992", "invalidIban!"];

    const openPreparedView = async () => {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create([
            {
                name: "Awesome partner",
                bank_ids: [pyEnv["res.partner.bank"].create([{ acc_number: "" }])],
            },
        ]);
        const views = {
            "res.partner,false,form": `<form>
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
        const { advanceTime, openView } = await start({
            serverData: { views },
            hasTimeControl: true,
            mockRPC: function (route, args) {
                if (args.method === "check_iban") {
                    const iban = args.args[1].replace(/\s/g, "");
                    return Promise.resolve(iban === validIban);
                }
            },
        });
        await openView({
            res_id: partnerId,
            res_model: "res.partner",
            views: [[false, "form"]],
        });
        return { advanceTime };
    };

    QUnit.test("Iban Widget full flow [REQUIRE FOCUS]", async () => {
        const { advanceTime } = await openPreparedView();
        await contains("td.o_iban_cell");
        await contains(".o_iban", { count: 0 }); // "Shouldn't display any validation icon while not editing a specific line"
        await click("td.o_iban_cell");
        await contains(".o_iban_input_with_validator");
        await contains(".o_iban", { count: 0 }); // "Shouldn't display any validation icon while iban is empty"
        await insertText(".o_iban_input_with_validator", invalidIban, { replace: true });
        await contains(".o_iban", { count: 0 }); // "Shouldn't change its state of display before edition is finished"
        await advanceTime(DELAY);
        await contains(".o_iban"); // "Should contain a validation icon 400ms after edition"
        await contains("i.fa.fa-times.o_iban_fail"); // "The validation icon should be the failed one"
        await contains("i.fa.fa-check.o_iban", { count: 0 }); // "The validation icon shouldn't be the successful one"
        await click(".o_form_button_save");
        await contains(".o_iban", { count: 0 }); // "Shouldn't display any validation while not editing"
        await click("td.o_iban_cell");
        await contains(".o_iban_input_with_validator");
        await advanceTime(DELAY);
        await contains("i.fa.fa-times.o_iban_fail"); // "The validation icon should be present while clicking on an already filled IBAN"
        await insertText(".o_iban_cell .o_input", validIban, { replace: true });
        await contains("i.fa.fa-times.o_iban_fail"); // "The validation icon shouldn't change during the edition"
        await advanceTime(DELAY);
        await contains(".o_iban"); // "Should contain a validation icon 400ms after edition"
        await contains("i.fa.fa-check.o_iban"); // "The validation icon should be the successful one"
        await contains("i.fa.fa-times.o_iban_fail", { count: 0 }); // "The validation icon shouldn't be the failed one"
        await click(".o_form_button_save");
        await contains(".o_iban", { count: 0 }); // "Shouldn't display any validation while not editing"
    });
});
