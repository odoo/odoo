/** @odoo-module **/

import { insertAndReplace } from '@mail/model/model_field_command';
import { afterEach, beforeEach, start } from '@mail/utils/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('clock_model_tests', {
    async beforeEach() {
        await beforeEach(this);

        this.start = async params => {
            const res = await start({ ...params, data: this.data });
            const { apps, env, widget } = res;
            this.apps = apps;
            this.env = env;
            this.widget = widget;
            return res;
        };
    },
    afterEach() {
        afterEach(this);
    },
});

QUnit.test('Deleting all the watchers of a clock should result in the deletion of the clock itself.', async function (assert) {
    assert.expect(1);

    await this.start();
    const watcher = this.messaging.models['ClockWatcher'].insert({
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
