/** @odoo-module **/

import { insertAndReplace, unlinkAll } from '@mail/model/model_field_command';
import { start } from '@mail/../tests/helpers/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('model_field_commands', {}, function () {
QUnit.module('unlink_all_tests.js');

QUnit.test('unlinkAll: should set x2one field undefined', async function (assert) {
    assert.expect(2);
    const { messaging } = await start();

    const contact = messaging.models['TestContact'].insert({
        id: 10,
        address: insertAndReplace({ id: 20 }),
    });
    const address = messaging.models['TestAddress'].findFromIdentifyingData({ id: 20 });
    contact.update({ address: unlinkAll() });
    assert.strictEqual(
        contact.address,
        undefined,
        'clear: should set x2one field undefined'
    );
    assert.strictEqual(
        address.contact,
        undefined,
        'the inverse relation should be cleared as well'
    );
});

QUnit.test('unlinkAll: should set x2many field an empty array', async function (assert) {
    assert.expect(2);
    const { messaging } = await start();

    const contact = messaging.models['TestContact'].insert({
        id: 10,
        tasks: insertAndReplace({
            id: 20,
        }),
    });
    const task = messaging.models['TestTask'].findFromIdentifyingData({ id: 20 });
    contact.update({ tasks: unlinkAll() });
    assert.strictEqual(
        contact.tasks.length,
        0,
        'clear: should set x2many field empty array'
    );
    assert.strictEqual(
        task.responsible,
        undefined,
        'the inverse relation should be cleared as well'
    );
});

});
});
