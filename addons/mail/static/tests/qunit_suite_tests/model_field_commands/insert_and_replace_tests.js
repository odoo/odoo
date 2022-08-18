/** @odoo-module **/

import { start } from '@mail/../tests/helpers/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('model_field_commands', {}, function () {
QUnit.module('insert_and_replace_tests.js');

QUnit.test('insertAndReplace: should create and link a new record for an empty x2one field', async function (assert) {
    assert.expect(2);
    const { messaging } = await start();

    const contact = messaging.models['TestContact'].insert({ id: 10 });
    contact.update({ address: { id: 10 } });
    const address = messaging.models['TestAddress'].findFromIdentifyingData({ id: 10 });
    assert.strictEqual(
        contact.address,
        address,
        'insertAndReplace: should create and link a record for an empty x2one field'
    );
    assert.strictEqual(
        address.contact,
        contact,
        'the inverse relation should be set as well'
    );
});

QUnit.test('insertAndReplace: should create and replace a new record for a non-empty x2one field', async function (assert) {
    assert.expect(3);
    const { messaging } = await start();

    const contact = messaging.models['TestContact'].insert({
        id: 10,
        address: { id: 10 },
    });
    const address10 = messaging.models['TestAddress'].findFromIdentifyingData({ id: 10 });
    contact.update({ address: { id: 20 } });
    const address20 = messaging.models['TestAddress'].findFromIdentifyingData({ id: 20 });
    assert.strictEqual(
        contact.address,
        address20,
        'insertAndReplace: should create and replace a new record for a non-empty x2one field'
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

QUnit.test('insertAndReplace: should update the existing record for an x2one field', async function (assert) {
    assert.expect(2);
    const { messaging } = await start();

    const contact = messaging.models['TestContact'].insert({
        id: 10,
        address: {
            id: 10,
            addressInfo: 'address 10',
        },
    });
    const address10 = messaging.models['TestAddress'].findFromIdentifyingData({ id: 10 });
    contact.update({
        address: {
            id: 10,
            addressInfo: 'address 10 updated',
        },
    });
    assert.strictEqual(
        contact.address,
        address10,
        'insertAndReplace: should not drop an existing record'
    );
    assert.strictEqual(
        address10.addressInfo,
        'address 10 updated',
        'insertAndReplace: should update the existing record for a x2one field'
    );
});

QUnit.test('insertAndReplace: should create and replace the records for an x2many field', async function (assert) {
    assert.expect(4);
    const { messaging } = await start();

    const contact = messaging.models['TestContact'].insert({
        id: 10,
        tasks: { id: 10 },
    });
    const task10 = messaging.models['TestTask'].findFromIdentifyingData({ id: 10 });
    contact.update({ tasks: { id: 20 } });
    const task20 = messaging.models['TestTask'].findFromIdentifyingData({ id: 20 });
    assert.strictEqual(
        contact.tasks.length,
        1,
        "should have 1 record"
    );
    assert.strictEqual(
        contact.tasks[0],
        task20,
        'task should be replaced by the new record'
    );
    assert.strictEqual(
        task20.responsible,
        contact,
        'the inverse relation should be set'
    );
    assert.strictEqual(
        task10.responsible,
        undefined,
        'the original relation should be dropped'
    );
});

QUnit.test('insertAndReplace: should update and replace the records for an x2many field', async function (assert) {
    assert.expect(4);
    const { messaging } = await start();

    const contact = messaging.models['TestContact'].insert({
        id: 10,
        tasks: [
            { id: 10, title: 'task 10' },
            { id: 20, title: 'task 20' },
        ],
    });
    const task10 = messaging.models['TestTask'].findFromIdentifyingData({ id: 10 });
    const task20 = messaging.models['TestTask'].findFromIdentifyingData({ id: 20 });
    contact.update({
        tasks: {
            id: 10,
            title: 'task 10 updated',
        },
    });
    assert.strictEqual(
        contact.tasks.length,
        1,
        "should have 1 record"
    );
    assert.strictEqual(
        contact.tasks[0],
        task10,
        'tasks should be replaced by new record'
    );
    assert.strictEqual(
        task10.title,
        'task 10 updated',
        'the record should be updated'
    );
    assert.strictEqual(
        task20.responsible,
        undefined,
        'the record should be replaced'
    );
});

});
});
