/** @odoo-module **/

import { clear, insertAndReplace, unlink } from '@mail/model/model_field_command';
import { start } from '@mail/../tests/helpers/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('model_field_commands', {}, function () {
QUnit.module('unlink_tests.js');


QUnit.test('unlink: should unlink the record for x2one field', async function (assert) {
    assert.expect(2);
    const { messaging } = await start();

    const contact = messaging.models['TestContact'].insert({
        id: 10,
        address: insertAndReplace({ id: 10 }),
    });
    const address = messaging.models['TestAddress'].findFromIdentifyingData({ id: 10 });
    contact.update({ address: clear() });
    assert.strictEqual(
        contact.address,
        undefined,
        'unlink: should unlink the record for x2one field'
    );
    assert.strictEqual(
        address.contact,
        undefined,
        'the original relation should be dropped as well'
    );
});

QUnit.test('unlink: should unlink the specified record for x2many field', async function (assert) {
    assert.expect(2);
    const { messaging } = await start();

    const contact = messaging.models['TestContact'].insert({
        id: 10,
        tasks: insertAndReplace([
            { id: 10 },
            { id: 20 },
        ]),
    });
    const task10 = messaging.models['TestTask'].findFromIdentifyingData({ id: 10 });
    const task20 = messaging.models['TestTask'].findFromIdentifyingData({ id: 20 });
    contact.update({ tasks: unlink(task10) });
    assert.ok(
        contact.tasks instanceof Array &&
        contact.tasks.length === 1 &&
        contact.tasks.includes(task20),
        'unlink: should unlink the specified record for x2many field'
    );
    assert.strictEqual(
        task10.responsible,
        undefined,
        'the orignal relation should be dropped as well'
    );
});

});
});
