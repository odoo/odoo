/** @odoo-module **/

import { create } from '@mail/model/model_field_command';
import { beforeEach } from '@mail/utils/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('model', {}, function () {
QUnit.module('model_field_command', {}, function () {
QUnit.module('create_tests.js', { beforeEach });

QUnit.test('create: should create and link a record for an empty x2one field', async function (assert) {
    assert.expect(2);

    const { messaging } = await this.start();

    const contact = messaging.models['test.contact'].create({ id: 10 });
    contact.update({ address: create({ id: 20 }) });
    const address = messaging.models['test.address'].findFromIdentifyingData({ id: 20 });
    assert.strictEqual(
        contact.address,
        address,
        'create: should create and link a record for an empty x2one field'
    );
    assert.strictEqual(
        address.contact,
        contact,
        'the inverse relation should be set as well'
    );
});

QUnit.test('create: should create and replace a record for a non-empty x2one field', async function (assert) {
    assert.expect(3);

    const { messaging } = await this.start();

    const contact = messaging.models['test.contact'].create({
        id: 10,
        address: create({ id: 10 }),
    });
    const address10 = messaging.models['test.address'].findFromIdentifyingData({ id: 10 });
    contact.update({ address: create({ id: 20 }) });
    const address20 = messaging.models['test.address'].findFromIdentifyingData({ id: 20 });
    assert.strictEqual(
        contact.address,
        address20,
        'create: should create and replace a record for a non-empty x2one field'
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

QUnit.test('create: should create and link a record for an empty x2many field', async function (assert) {
    assert.expect(3);

    const { messaging } = await this.start();

    const contact = messaging.models['test.contact'].create({ id: 10 });
    contact.update({ tasks: create({ id: 10 }) });
    const task = messaging.models['test.task'].findFromIdentifyingData({ id: 10 });
    assert.strictEqual(
        contact.tasks.length,
        1,
        'should have 1 record'
    );
    assert.strictEqual(
        contact.tasks[0],
        task,
        'should link the record for an empty x2many field'
    );
    assert.strictEqual(
        task.responsible,
        contact,
        'the inverse relation should be set as well'
    );
});

QUnit.test('create: should create and add a record for a non-empty x2many field', async function (assert) {
    assert.expect(4);

    const { messaging } = await this.start();

    const contact = messaging.models['test.contact'].create({
        id: 10,
        tasks: create({
            id: 10,
        }),
    });
    const task10 = messaging.models['test.task'].findFromIdentifyingData({ id: 10 });
    contact.update({ tasks: create({ id: 20 }) });
    const task20 = messaging.models['test.task'].findFromIdentifyingData({ id: 20 });
    assert.strictEqual(
        contact.tasks.length,
        2,
        "should have 2 records"
    );
    assert.strictEqual(
        contact.tasks[0],
        task10,
        "the original record should be there"
    );
    assert.strictEqual(
        contact.tasks[1],
        task20,
        'the new record should be added'
    );
    assert.strictEqual(
        task20.responsible,
        contact,
        'the inverse relation should be set as well'
    );
});

});
});
});
