/** @odoo-module **/

import { create } from 'mail/static/src/model/model_field_command.js';
import {
    afterEach,
    beforeEach,
    start,
} from 'mail/static/src/utils/test_utils.js';

QUnit.module('mail', {}, function () {
QUnit.module('model', {}, function () {
QUnit.module('model_field_command', {}, function () {
QUnit.module('create_tests.js', {
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

QUnit.test('create: should create and link a record for an empty x2one field', async function (assert) {
    assert.expect(2);
    await this.start();

    const contact = this.env.models['test.contact'].create({ id: 10 });
    contact.update({ address: create({ id: 20 })});
    const address = this.env.models['test.address'].findFromIdentifyingData({ id: 20 });
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
    await this.start();

    const contact = this.env.models['test.contact'].create({
        id: 10,
        address: create({ id: 10 }),
    });
    const address10 = this.env.models['test.address'].findFromIdentifyingData({ id: 10 });
    contact.update({ address: create({ id: 20 })});
    const address20 = this.env.models['test.address'].findFromIdentifyingData({ id: 20 });
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
    await this.start();

    const contact = this.env.models['test.contact'].create({ id: 10 });
    contact.update({ tasks: create({ id: 10 }) });
    const task = this.env.models['test.task'].findFromIdentifyingData({ id: 10 });
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
    await this.start();

    const contact = this.env.models['test.contact'].create({
        id: 10,
        tasks: create({
            id: 10,
        }),
    });
    const task10 = this.env.models['test.task'].findFromIdentifyingData({ id: 10 });
    contact.update({ tasks: create({ id: 20 }) });
    const task20 = this.env.models['test.task'].findFromIdentifyingData({ id: 20 });
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
