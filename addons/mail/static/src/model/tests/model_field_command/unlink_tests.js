/** @odoo-module **/

import { insertAndReplace, unlink } from '@mail/model/model_field_command';
import {
    afterEach,
    beforeEach,
    start,
} from '@mail/utils/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('model', {}, function () {
QUnit.module('model_field_command', {}, function () {
QUnit.module('unlink_tests.js', {
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


QUnit.test('unlink: should unlink the record for x2one field', async function (assert) {
    assert.expect(2);
    await this.start();

    const contact = this.messaging.models['test.contact'].create({
        id: 10,
        address: insertAndReplace({ id: 10 }),
    });
    const address = this.messaging.models['test.address'].findFromIdentifyingData({ id: 10 });
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
    await this.start();

    const contact = this.messaging.models['test.contact'].create({
        id: 10,
        tasks: insertAndReplace([
            { id: 10 },
            { id: 20 },
        ]),
    });
    const task10 = this.messaging.models['test.task'].findFromIdentifyingData({ id: 10 });
    const task20 = this.messaging.models['test.task'].findFromIdentifyingData({ id: 20 });
    contact.update({ tasks: unlink(task10) });
    assert.ok(
        contact.tasks instanceof Array &&
        contact.tasks.length === 1 &&
        contact.tasks.includes(task20),
        'unlink: should unlink the specified record for x2many field'
    );
    assert.strictEqual(
        task10.responsible,
        undefined,
        'the orignal relation should be dropped as well'
    );
});

});
});
});
