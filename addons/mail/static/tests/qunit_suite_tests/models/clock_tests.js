/** @odoo-module **/

import { insertAndReplace } from '@mail/model/model_field_command';
import { start } from '@mail/../tests/helpers/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('models', {}, function () {
QUnit.module('clock_tests.js');

QUnit.test('Deleting all the watchers of a clock should result in the deletion of the clock itself.', async function (assert) {
    assert.expect(1);

    const { messaging } = await start();
    const watcher = messaging.models['ClockWatcher'].insert({
        clock: insertAndReplace({ frequency: 180 * 1000 }),
        qunitTestOwner: insertAndReplace(),
    });
    const { clock } = watcher;

    watcher.delete();
    assert.notOk(
        clock.exists(),
        "deleting all the watchers of a clock should result in the deletion of the clock itself."
    );
});

});
});
