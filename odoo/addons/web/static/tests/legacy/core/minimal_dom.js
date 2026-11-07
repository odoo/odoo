/** @odoo-module **/
import { registerCleanup } from "@web/../tests/helpers/cleanup";
import { getFixture, nextTick } from "@web/../tests/helpers/utils";
import { DEBOUNCE, makeAsyncHandler, makeButtonHandler } from '@web/legacy/js/core/minimal_dom';

QUnit.module('core', {}, function () {

    QUnit.module('MinimalDom');

    QUnit.test('MakeButtonHandler does not retrigger the same error', async function (assert) {
        assert.expect(1);
        assert.expectErrors();

        // create a target for the button handler
        const fixture = getFixture();
        const button = document.createElement("button");
        fixture.appendChild(button);
        registerCleanup(() => { button.remove(); });

        // get a way to reject the promise later
        let rejectPromise;
        const buttonHandler = makeButtonHandler(() => new Promise((resolve, reject) => {
            rejectPromise = reject;
        }));

        // trigger the handler
        buttonHandler({ target: button });

        // wait for the button effect has been applied before rejecting the promise
        await new Promise(res => setTimeout(res, DEBOUNCE + 1));
        rejectPromise(new Error("reject"));

        // check that there was only one unhandledrejection error
        await nextTick();
        assert.verifyErrors(["reject"]);
    });

    QUnit.test('MakeAsyncHandler does not retrigger the same error', async function (assert) {
        assert.expect(1);
        assert.expectErrors();

        // get a way to reject the promise later
        let rejectPromise;
        const asyncHandler = makeAsyncHandler(() => new Promise((resolve, reject) => {
            rejectPromise = reject;
        }));

        // trigger the handler
        asyncHandler();

        rejectPromise(new Error("reject"));

        // check that there was only one unhandledrejection error
        await nextTick();
        assert.verifyErrors(["reject"]);
    });
});
