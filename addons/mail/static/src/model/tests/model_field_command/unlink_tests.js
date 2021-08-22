/** @odoo-module **/

import { create, unlink } from '@mail/model/model_field_command';
import { beforeEach } from '@mail/utils/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('model', {}, function () {
QUnit.module('model_field_command', {}, function () {
QUnit.module('unlink_tests.js', { beforeEach });


QUnit.test('unlink: should unlink the record for x2one field', async function (assert) {
    assert.expect(2);

    const { messaging } = await this.start();

    const contact = messaging.models['test.contact'].create({
        id: 10,
        address: create({ id: 10 }),
    });
    const address = messaging.models['test.address'].findFromIdentifyingData({ id: 10 });
    contact.update({ address: unlink() });
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
    contact.update({ tasks: unlink(task10) });
    assert.ok(
        contact.tasks instanceof Array &&
        contact.tasks.length === 1 &&
        contact.tasks.includes(task20),
        'unlink: should unlink the specified record for x2many field'
    );
    assert.strictEqual(
        task20.contact,
        undefined,
        'the orignial relation should be dropped as well'
    );
});

});
});
});
