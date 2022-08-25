/** @odoo-module **/

import { makeDeferred } from '@mail/utils/deferred';
import { start } from '@mail/../tests/helpers/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('dialog_manager_tests.js');

QUnit.test('[technical] messaging not created', async function (assert) {
    /**
     * Creation of messaging in env is async due to generation of models being
     * async. Generation of models is async because it requires parsing of all
     * JS modules that contain pieces of model definitions.
     *
     * Time of having no messaging is very short, almost imperceptible by user
     * on UI, but the display should not crash during this critical time period.
     */
    assert.expect(1);

    const messagingBeforeCreationDeferred = makeDeferred();
    const { afterNextRender } = await start({
        messagingBeforeCreationDeferred,
        waitUntilMessagingCondition: 'none',
    });

    // simulate messaging being created
    await afterNextRender(messagingBeforeCreationDeferred.resolve);

    assert.containsOnce(
        document.body,
        '.o_DialogManager',
        "should contain dialog manager after messaging has been created"
    );
});

QUnit.test('initial mount', async function (assert) {
    assert.expect(1);

    await start();
    assert.containsOnce(
        document.body,
        '.o_DialogManager',
        "should have dialog manager"
    );
});

});
});
