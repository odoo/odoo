/** @odoo-module **/

import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { insufficientCreditHandler } from "../src/js/insufficient_credit_error_handler";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";

QUnit.module("iap", (hooks) => {
    let env;

    hooks.beforeEach(async () => {
        env = await makeTestEnv();
        env.services.dialog = {
            add: (Component, props) => {
                env.__dialogComponent = Component;
                env.__dialogProps = props;
            },
        };
    });

    QUnit.test("displays AlertDialog when data.message is missing", async (assert) => {
        const originalError = {
            data: {
                name: "odoo.addons.iap.tools.iap_tools.InsufficientCreditError",
                // no `message` field
            },
        };

        const handled = insufficientCreditHandler(env, {}, originalError);

        assert.ok(handled, "Error should be handled");
        assert.strictEqual(env.__dialogComponent, AlertDialog, "Should render AlertDialog");
        assert.deepEqual(env.__dialogProps, {
            title: "Insufficient Credit Error",
            body: "Insufficient credit to perform this service.",
        }, "Dialog should have correct title and body");
    });
});
