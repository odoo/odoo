/** @odoo-module **/

import { create, clear } from 'mail/static/src/model/model_field_command.js';
import {
    afterEach,
    beforeEach,
    start,
} from 'mail/static/src/utils/test_utils.js';

QUnit.module('mail', {}, function () {
QUnit.module('model', {}, function () {
QUnit.module('model_field_command', {}, function () {
QUnit.module('clear_tests.js', {
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
QUnit.test('clear: should set attribute field undefined if there is no default value', async function (assert) {
    assert.expect(1);

    await this.start();
    const task = this.env.models['test.task'].create({
        id: 1,
        title: 'test title 1',
    });
    task.update({ title: clear() });
    assert.strictEqual(
        task.title,
        undefined,
        'clear: should set attribute field undefined if there is no default value'
    );
});

QUnit.test('clear: should set attribute field the default value', async function (assert) {
    assert.expect(1);

    await this.start();
    const task = this.env.models['test.task'].create({
        id: 1,
        difficulty: 5,
    });
    task.update({ difficulty: clear() });
    assert.strictEqual(
        task.difficulty,
        1,
        'clear: should set attribute field the default value'
    );
});

QUnit.test('clear: should set x2one field undefined if no default value is given', async function (assert) {
    assert.expect(2);
    await this.start();

    const contact = this.env.models['test.contact'].create({
        id: 10,
        address: create({ id: 20 }),
    });
    const address = this.env.models['test.address'].findFromIdentifyingData({ id: 20 });
    contact.update({ address: clear() });
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

QUnit.test('clear: should set x2one field the default value', async function (assert) {
    assert.expect(1);
    await this.start();

    const contact = this.env.models['test.contact'].create({
        favorite: create({ description: 'pingpong' }),
    });
    contact.update({ favorite: clear() });
    assert.strictEqual(
        contact.favorite.description,
        'football',
        'clear: should set x2one field default value'
    );
});

QUnit.test('clear: should set x2many field empty array if no default value is given', async function (assert) {
    assert.expect(2);
    await this.start();

    const contact = this.env.models['test.contact'].create({
        id: 10,
        tasks: create({ id: 20 }),
    });
    const task = this.env.models['test.task'].findFromIdentifyingData({ id:20 });
    contact.update({ tasks: clear() });
    assert.ok(
        contact.tasks instanceof Array &&
        contact.tasks.length === 0,
        'clear: should set x2many field empty array'
    );
    assert.strictEqual(
        task.responsible,
        undefined,
        'the inverse relation should be cleared as well'
    );
});

QUnit.test('clear: should set x2many field the default value', async function (assert) {
    assert.expect(1);
    await this.start();

    const contact = this.env.models['test.contact'].create({
        id: 10,
        hobbies: [
            create({ description: 'basketball' }),
            create({ description: 'running' }),
            create({ description: 'photographing'})
        ],
    });
    contact.update({ hobbies: clear() });
    const hobbyDescriptions = contact.hobbies.map(h => h.description);
    assert.deepEqual(
        hobbyDescriptions,
        ['hiking', 'fishing'],
        'clear: should set x2many field the default value',
    );
});

});
});
});
