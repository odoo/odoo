/** @odoo-module **/

import {
    decrement,
    increment,
    set
} from '@mail/model/model_field_command';
import { start } from '@mail/../tests/helpers/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('model_field_commands', {}, function () {
QUnit.module('set_tests.js');

QUnit.test('decrement: should decrease attribute field value', async function (assert) {
    assert.expect(1);
    const { messaging } = await start();

    const task = messaging.models['TestTask'].insert({
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
    const { messaging } = await start();

    const task = messaging.models['TestTask'].insert({
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
    const { messaging } = await start();

    const task = messaging.models['TestTask'].insert({
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
    const { messaging } = await start();

    const task = messaging.models['TestTask'].insert({
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
