odoo.define('web.crash_manager_tests', function (require) {
    "use strict";
    const CrashManager = require('web.CrashManager').CrashManager;
    const Bus = require('web.Bus');
    const testUtils = require('web.test_utils');
    const core = require('web.core');
    const createActionManager = testUtils.createActionManager;
    
QUnit.module('Services', {}, function() {

    QUnit.module('CrashManager');

    QUnit.test("Execute an action and close the RedirectWarning when clicking on the primary button", async function (assert) {
        assert.expect(4);

        var dummy_action_name = "crash_manager_tests_dummy_action";
        var dummy_action = function() {
                assert.step('do_action');
            };
        core.action_registry.add(dummy_action_name, dummy_action);

        // What we want to test is a do-action triggered by the crashManagerService
        // the intercept feature of testUtilsMock is not fit for this, because it is too low in the hierarchy
        const bus = new Bus();
        bus.on('do-action', null, payload => {
            const { action, options } = payload;
            actionManager.doAction(action, options);
        });

        var actionManager = await createActionManager({
            actions: [dummy_action],
            services: {
                crash_manager: CrashManager,
            },
            bus
        });
        actionManager.call('crash_manager', 'rpc_error', {
            code: 200,
            data: {
                name: "odoo.exceptions.RedirectWarning",
                arguments: [
                    "crash_manager_tests_warning_modal_text",
                    dummy_action_name,
                    "crash_manager_tests_button_text",
                    null,
                ]
            }
        });
        await testUtils.nextTick();

        var modal_selector = 'div.modal:contains("crash_manager_tests_warning_modal_text")';
        assert.containsOnce($, modal_selector, "Warning Modal should be opened");

        await testUtils.dom.click($(modal_selector).find('button.btn-primary'));

        assert.containsNone($, modal_selector, "Warning Modal should be closed");
        assert.verifySteps(['do_action'], "Warning Modal Primary Button Action should be executed");
        
        actionManager.destroy();
    });
});
});
