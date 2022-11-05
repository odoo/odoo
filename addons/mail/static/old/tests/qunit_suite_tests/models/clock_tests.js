/** @odoo-module **/

import { start } from '@mail/../tests/helpers/test_utils';

import { patchDate } from '@web/../tests/helpers/utils';

QUnit.module('mail', {}, function () {
QUnit.module('models', {}, function () {
QUnit.module('clock_tests.js');

QUnit.test('Deleting all the watchers of a clock should result in the deletion of the clock itself.', async function (assert) {
    assert.expect(1);

    const { messaging } = await start();
    const watcher = messaging.models['ClockWatcher'].insert({
        clock: { frequency: 180 * 1000 },
        qunitTestOwner: {},
    });
    const { clock } = watcher;

    watcher.delete();
    assert.notOk(
        clock.exists(),
        "deleting all the watchers of a clock should result in the deletion of the clock itself."
    );
});

QUnit.test('[technical] Before ticking for the first time, the clock should indicate the date of creation of the record.', async function (assert) {
    assert.expect(1);

    const { messaging } = await start();
    // The date is patched AFTER startup, so if the date field in Clock was set
    // at initialization (which we don't want), it will now look completely
    // different from the patched date.
    patchDate(2016, 8, 8, 14, 55, 15, 352);

    const { clock } = messaging.models['ClockWatcher'].insert({
        clock: { frequency: 3600 * 1000 },
        qunitTestOwner: {},
    });
    assert.strictEqual(
        clock.date.getFullYear(), // no need to be more precise than the year
        2016,
        "before ticking for the first time, the clock should indicate the date of creation of the record."
    );
});

});
});
