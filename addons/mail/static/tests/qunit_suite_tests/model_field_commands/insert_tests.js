/** @odoo-module **/

import { insert, insertAndReplace } from '@mail/model/model_field_command';
import { start } from '@mail/../tests/helpers/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('model_field_commands', {}, function () {
QUnit.module('insert_tests.js');

QUnit.test('insert: should create and link a new record for an empty x2one field', async function (assert) {
    assert.expect(2);
    const { messaging } = await start();

    const contact = messaging.models['TestContact'].insert({ id: 10 });
    contact.update({ address: insert({ id: 10 }) });
    const address = messaging.models['TestAddress'].findFromIdentifyingData({ id: 10 });
    assert.strictEqual(
        contact.address,
        address,
        'insert: should create and link a record for an empty x2one field'
    );
    assert.strictEqual(
        address.contact,
        contact,
        'the inverse relation should be set as well'
    );
});

QUnit.test('insert: should create and replace a new record for a non-empty x2one field', async function (assert) {
    assert.expect(3);
    const { messaging } = await start();

    const contact = messaging.models['TestContact'].insert({
        id: 10,
        address: insertAndReplace({ id: 10 }),
    });
    const address10 = messaging.models['TestAddress'].findFromIdentifyingData({ id: 10 });
    contact.update({ address: insert({ id: 20 }) });
    const address20 = messaging.models['TestAddress'].findFromIdentifyingData({ id: 20 });
    assert.strictEqual(
        contact.address,
        address20,
        'insert: should create and replace a new record for a non-empty x2one field'
    );
    assert.strictEqual(
        address20.contact,
        contact,
        'the inverse relation should be set as well'
    );
    assert.strictEqual(
        address10.contact,
        undefined,
        'the original relation should be dropped'
    );
});

QUnit.test('insert: should update the existing record for an x2one field', async function (assert) {
    assert.expect(2);
    const { messaging } = await start();

    const contact = messaging.models['TestContact'].insert({
        id: 10,
        address: insertAndReplace({
            id: 10,
            addressInfo: 'address 10',
        }),
    });
    const address10 = messaging.models['TestAddress'].findFromIdentifyingData({ id: 10 });
    contact.update({
        address: insert({
            id: 10,
            addressInfo: 'address 10 updated',
        }),
    });
    assert.strictEqual(
        contact.address,
        address10,
        'insert: should not drop an existing record'
    );
    assert.strictEqual(
        address10.addressInfo,
        'address 10 updated',
        'insert: should update the existing record for a x2one field'
    );
});

QUnit.test('insert: should create and link a new record for an x2many field', async function (assert) {
    assert.expect(3);
    const { messaging } = await start();

    const contact = messaging.models['TestContact'].insert({ id: 10 });
    contact.update({ tasks: insert({ id: 10 }) });
    const task = messaging.models['TestTask'].findFromIdentifyingData({ id: 10 });
    assert.strictEqual(
        contact.tasks.length,
        1,
        'should have 1 record'
    );
    assert.strictEqual(
        contact.tasks[0],
        task,
        "should link the new record"
    );
    assert.strictEqual(
        task.responsible,
        contact,
        'the inverse relation should be set as well'
    );
});

QUnit.test('insert: should create and add a new record for an x2many field', async function (assert) {
    assert.expect(4);
    const { messaging } = await start();

    const contact = messaging.models['TestContact'].insert({
        id: 10,
        tasks: insertAndReplace({ id: 10 }),
    });
    const task10 = messaging.models['TestTask'].findFromIdentifyingData({ id: 10 });
    contact.update({ tasks: insert({ id: 20 }) });
    const task20 = messaging.models['TestTask'].findFromIdentifyingData({ id: 20 });
    assert.strictEqual(
        contact.tasks.length,
        2,
        "should have 2 records"
    );
    assert.strictEqual(
        contact.tasks[0],
        task10,
        "the original record should be kept"
    );
    assert.strictEqual(
        contact.tasks[1],
        task20,
        'new record should be added'
    );
    assert.strictEqual(
        task20.responsible,
        contact,
        'the inverse relation should be set as well'
    );
});

QUnit.test('insert: should update existing records for an x2many field', async function (assert) {
    assert.expect(3);
    const { messaging } = await start();

    const contact = messaging.models['TestContact'].insert({
        id: 10,
        tasks: insertAndReplace({
            id: 10,
            title: 'task 10',
        }),
    });
    const task = messaging.models['TestTask'].findFromIdentifyingData({ id: 10 });
    contact.update({
        tasks: insert({
            id: 10,
            title: 'task 10 updated',
        }),
    });
    assert.strictEqual(
        contact.tasks.length,
        1,
        "should have 1 record"
    );
    assert.strictEqual(
        contact.tasks[0],
        task,
        "the original task should be kept"
    );
    assert.strictEqual(
        task.title,
        'task 10 updated',
        'should update the existing record'
    );
});

});
});
