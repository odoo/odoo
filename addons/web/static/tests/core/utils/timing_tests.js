/** @odoo-module **/

import { debouncePromise } from "@web/core/utils/timing";

QUnit.module("utils", () => {
    QUnit.module("timing");

    QUnit.test("debouncePromise", async function (assert) {
        const myFunc = () => {
            assert.step("exec");
        };
        const myDebouncedFunc = debouncePromise(myFunc, 10);
        let toAwait = myDebouncedFunc();
        assert.verifySteps([]);
        toAwait = myDebouncedFunc();
        await toAwait;
        assert.verifySteps(["exec"]);
    });
});
