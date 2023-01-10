/** @odoo-module **/

import { insertAndReplace } from '@mail/model/model_field_command';
import {
    afterEach,
    beforeEach,
    start,
} from '@mail/utils/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('model', {}, function () {
QUnit.module('model_field_command', {}, function () {
QUnit.module('insert_and_replace_tests.js', {
    beforeEach() {
        beforeEach(this);
        this.start = async params => {
            const { env, widget } = await start(Object.assign({}, params, {
                data: this.data,
            }));
            this.env = env;
            this.widget = widget;
        };
    },
    afterEach() {
        afterEach(this);
    },
});

QUnit.test('insertAndReplace: should create and link a new record for an empty x2one field', async function (assert) {
    assert.expect(2);
    await this.start();

    const contact = this.messaging.models['test.contact'].create({ id: 10 });
    contact.update({ address: insertAndReplace({ id: 10 }) });
    const address = this.messaging.models['test.address'].findFromIdentifyingData({ id: 10 });
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
    await this.start();

    const contact = this.messaging.models['test.contact'].create({
        id: 10,
        address: insertAndReplace({ id: 10 }),
    });
    const address10 = this.messaging.models['test.address'].findFromIdentifyingData({ id: 10 });
    contact.update({ address: insertAndReplace({ id: 20 }) });
    const address20 = this.messaging.models['test.address'].findFromIdentifyingData({ id: 20 });
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
    await this.start();

    const contact = this.messaging.models['test.contact'].create({
        id: 10,
        address: insertAndReplace({
            id: 10,
            addressInfo: 'address 10',
        }),
    });
    const address10 = this.messaging.models['test.address'].findFromIdentifyingData({ id: 10 });
    contact.update({
        address: insertAndReplace({
            id: 10,
            addressInfo: 'address 10 updated',
        }),
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
    await this.start();

    const contact = this.messaging.models['test.contact'].create({
        id: 10,
        tasks: insertAndReplace({ id: 10 }),
    });
    const task10 = this.messaging.models['test.task'].findFromIdentifyingData({ id: 10 });
    contact.update({ tasks: insertAndReplace({ id: 20 }) });
    const task20 = this.messaging.models['test.task'].findFromIdentifyingData({ id: 20 });
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
    await this.start();

    const contact = this.messaging.models['test.contact'].create({
        id: 10,
        tasks: insertAndReplace([
            { id: 10, title: 'task 10' },
            { id: 20, title: 'task 20' },
        ]),
    });
    const task10 = this.messaging.models['test.task'].findFromIdentifyingData({ id: 10 });
    const task20 = this.messaging.models['test.task'].findFromIdentifyingData({ id: 20 });
    contact.update({
        tasks: insertAndReplace({
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
});
