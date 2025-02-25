import { BaseAutomationErrorDialog } from "@base_automation/base_automation_error_dialog";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import {
    makeServerError,
    mountWithCleanup,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { MainComponentsContainer } from "@web/core/main_components_container";

defineMailModels();

test("Error due to an automation rule", async () => {
    expect.errors(1);
    const errorContext = {
        exception_class: "base_automation",
        base_automation: {
            id: 1,
            name: "Test base automation error dialog",
        },
    };
    const error = makeServerError({
        subType: "Odoo Client Error",
        message: "Message",
        context: errorContext,
        errorName: "automation error",
    });

    patchWithCleanup(BaseAutomationErrorDialog.prototype, {
        setup() {
            expect(this.props.data.context).toEqual(errorContext);
            expect.step("error setup");
            super.setup();
        },
    });
    await mountWithCleanup(MainComponentsContainer);
    Promise.reject(error);
    await animationFrame();
    expect.verifyErrors(["Message"]);
    expect.verifySteps(["error setup"]);
    expect(".modal .modal-footer .o_disable_action_button").toHaveCount(1);
    expect(".modal .modal-footer .o_edit_action_button").toHaveCount(1);
});

test("Error not due to an automation rule", async () => {
    expect.errors(1);
    const error = makeServerError({
        subType: "Odoo Client Error",
        message: "Message",
        errorName: "non automation error",
    });

    await mountWithCleanup(MainComponentsContainer);

    Promise.reject(error);
    await animationFrame();
    expect.verifyErrors(["Message"]);
    expect(".modal .modal-footer .o_disable_action_button").toHaveCount(0);
    expect(".modal .modal-footer .o_edit_action_button").toHaveCount(0);
});

test("display automation rule id and name in Error dialog", async () => {
    expect.errors(1);
    const errorContext = {
        exception_class: "base_automation",
        base_automation: {
            id: 1,
            name: "Test base automation error dialog",
        },
    };
    const error = makeServerError({
        subType: "Odoo Client Error",
        message: "Message",
        context: errorContext,
        errorName: "automation error",
    });

    patchWithCleanup(BaseAutomationErrorDialog.prototype, {
        setup() {
            expect(this.props.data.context).toEqual(errorContext);
            expect.step("error setup");
            super.setup();
        },
    });
    await mountWithCleanup(MainComponentsContainer);
    Promise.reject(error);
    await animationFrame();
    expect.verifyErrors(["Message"]);
    expect.verifySteps(["error setup"]);
    expect(".modal-body p:nth-child(2)").toHaveText(
        `The error occurred during the execution of the automation rule "Test base automation error dialog" (ID: 1).`
    );
});
