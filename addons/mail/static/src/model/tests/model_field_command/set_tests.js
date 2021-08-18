/** @odoo-module **/

import {
    decrement,
    increment,
    set
} from '@mail/model/model_field_command';
import {
    afterEach,
    beforeEach,
    start,
} from '@mail/utils/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('model', {}, function () {
QUnit.module('model_field_command', {}, function () {
QUnit.module('set_tests.js', {
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

QUnit.test('decrement: should decrease attribute field value', async function (assert) {
    assert.expect(1);
    await this.start();

    const task = this.messaging.models['test.task'].create({
        id: 10,
        difficulty: 5,
    });
    task.update({ difficulty: decrement(2) });
    assert.strictEqual(
        task.difficulty,
        5 - 2,
        'decrement: should decrease attribute field value'
    );
});

QUnit.test('increment: should increase attribute field value', async function (assert) {
    assert.expect(1);
    await this.start();

    const task = this.messaging.models['test.task'].create({
        id: 10,
        difficulty: 5,
    });
    task.update({ difficulty: increment(3) });
    assert.strictEqual(
        task.difficulty,
        5 + 3,
        'decrement: should increase attribute field value'
    );
});

QUnit.test('set: should set a value for attribute field', async function (assert) {
    assert.expect(1);
    await this.start();

    const task = this.messaging.models['test.task'].create({
        id: 10,
        difficulty: 5,
    });
    task.update({ difficulty: set(20) });
    assert.strictEqual(
        task.difficulty,
        20,
        'set: should set a value for attribute field'
    );
});

QUnit.test('multiple attribute commands combination', async function (assert) {
    assert.expect(1);
    await this.start();

    const task = this.messaging.models['test.task'].create({
        id: 10,
        difficulty: 5,
    });
    task.update({
        difficulty: [
            set(20),
            increment(16),
            decrement(8),
        ],
    });
    assert.strictEqual(
        task.difficulty,
        20 + 16 - 8,
        'multiple attribute commands combination should work as expected'
    );
});

});
});
});
