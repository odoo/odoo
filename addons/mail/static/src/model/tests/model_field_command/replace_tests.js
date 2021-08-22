/** @odoo-module **/

import { create, replace } from '@mail/model/model_field_command';
import { beforeEach } from '@mail/utils/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('model', {}, function () {
QUnit.module('model_field_command', {}, function () {
QUnit.module('replace_tests.js', { beforeEach });

QUnit.test('replace: should link a record for an empty x2one field', async function (assert) {
    assert.expect(2);

    const { messaging } = await this.start();

    const contact = messaging.models['test.contact'].create({ id: 10 });
    const address = messaging.models['test.address'].create({ id: 10 });
    contact.update({ address: replace(address) });
    assert.strictEqual(
        contact.address,
        address,
        'replace: should link a record for an empty x2one field'
    );
    assert.strictEqual(
        address.contact,
        contact,
        'the inverse relation should be set as well'
    );
});

QUnit.test('replace: should replace a record for a non-empty x2one field', async function (assert) {
    assert.expect(3);

    const { messaging } = await this.start();

    const contact = messaging.models['test.contact'].create({
        id: 10,
        address: create({ id: 10 }),
    });
    const address10 = messaging.models['test.address'].findFromIdentifyingData({ id: 10 });
    const address20 = messaging.models['test.address'].create({ id: 20 });
    contact.update({ address: replace(address20) });
    assert.strictEqual(
        contact.address,
        address20,
        'replace: should replace a record for a non-empty x2one field'
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

QUnit.test('replace: should link a record for an empty x2many field', async function (assert) {
    assert.expect(4);

    const { messaging } = await this.start();

    const contact = messaging.models['test.contact'].create({ id: 10 });
    const task = messaging.models['test.task'].create({ id: 10 });
    contact.update({ tasks: replace(task) });
    assert.strictEqual(
        contact.tasks.length,
        1,
        "should have 1 record"
    );
    assert.strictEqual(
        contact.tasks.length,
        1,
        "should have 1 record"
    );
    assert.strictEqual(
        contact.tasks[0],
        task,
        "the new record should be linked"
    );
    assert.strictEqual(
        task.responsible,
        contact,
        'the inverse relation should be dropped'
    );
});

QUnit.test('replace: should replace all records for a non-empty field', async function (assert) {
    assert.expect(5);

    const { messaging } = await this.start();

    const contact = messaging.models['test.contact'].create({
        id: 10,
        tasks: create([
            { id: 10 },
            { id: 20 },
        ]),
    });
    const task10 = messaging.models['test.task'].findFromIdentifyingData({ id: 10 });
    const task20 = messaging.models['test.task'].findFromIdentifyingData({ id: 20 });
    const task30 = messaging.models['test.task'].create({ id: 30 });
    contact.update({ tasks: replace(task30) });
    assert.strictEqual(
        contact.tasks.length,
        1,
        "should have 1 record"
    );
    assert.strictEqual(
        contact.tasks[0],
        task30,
        'should be replaced with the new record'
    );
    assert.strictEqual(
        task30.responsible,
        contact,
        'the inverse relation should be set as well'
    );
    assert.strictEqual(
        task10.responsible,
        undefined,
        'the original relation should be dropped'
    );
    assert.strictEqual(
        task20.responsible,
        undefined,
        'the original relation should be dropped'
    );
});

QUnit.test('replace: should order the existing records for x2many field', async function (assert) {
    assert.expect(3);

    const { messaging } = await this.start();

    const contact = messaging.models['test.contact'].create({
        id: 10,
        tasks: create([
            { id: 10 },
            { id: 20 },
        ]),
    });
    const task10 = messaging.models['test.task'].findFromIdentifyingData({ id: 10 });
    const task20 = messaging.models['test.task'].findFromIdentifyingData({ id: 20 });
    contact.update({
        tasks: replace([task20, task10]),
    });
    assert.strictEqual(
        contact.tasks.length,
        2,
        "should have 2 records"
    );
    assert.strictEqual(
        contact.tasks[0],
        task20,
        'records should be re-ordered'
    );
    assert.strictEqual(
        contact.tasks[1],
        task10,
        'recprds should be re-ordered'
    );
});

});
});
});
