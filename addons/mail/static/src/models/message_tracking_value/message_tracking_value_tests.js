/** @odoo-module **/
import { insert } from '@mail/model/model_field_command';
import {
    afterEach,
    beforeEach,
    nextAnimationFrame,
    start,
} from '@mail/utils/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('models', {}, function () {
QUnit.module('message_tracking_value', {}, function () {
QUnit.module('message_tracking_value_tests.js', {
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

QUnit.test('model test of tracking value (float type)', async function (assert) {
    assert.expect(6);

    await this.start();
    const message = this.env.models['mail.message'].create({
        id: 11,
        trackingValues: insert({
            changedField: "Total",
            fieldType: "float",
            id: 6,
            newValue: 45.67,
            oldValue: 12.3,
        }),
    });
    assert.ok(this.env.models['mail.message_tracking_value'].findFromIdentifyingData({ id: 6 }));
    assert.ok(message);
    assert.strictEqual(this.env.models['mail.message'].findFromIdentifyingData({ id: 11 }), message);
    assert.strictEqual(message.trackingValues[0].changedFieldAsString, "Total:");
    assert.strictEqual(message.trackingValues[0].newValueAsString, "45.67");
    assert.strictEqual(message.trackingValues[0].oldValueAsString, "12.30");
});

QUnit.test('model test of tracking value of type integer: from non-0 to 0', async function (assert) {
    assert.expect(6);

    await this.start();
    const message = this.env.models['mail.message'].create({
        id: 11,
        trackingValues: insert({
            changedField: "Total",
            fieldType: "integer",
            id: 6,
            newValue: 0,
            oldValue: 1,
        }),
    });
    assert.ok(this.env.models['mail.message_tracking_value'].findFromIdentifyingData({ id: 6 }));
    assert.ok(message);
    assert.strictEqual(this.env.models['mail.message'].findFromIdentifyingData({ id: 11 }), message);
    assert.strictEqual(message.trackingValues[0].changedFieldAsString, "Total:");
    assert.strictEqual(message.trackingValues[0].newValueAsString, "0");
    assert.strictEqual(message.trackingValues[0].oldValueAsString, "1");
});

QUnit.test('model test of tracking value of type integer: from 0 to non-0', async function (assert) {
    assert.expect(6);

    await this.start();
    const message = this.env.models['mail.message'].create({
        id: 11,
        trackingValues: insert({
            changedField: "Total",
            fieldType: "integer",
            id: 6,
            newValue: 1,
            oldValue: 0,
        }),
    });
    assert.ok(this.env.models['mail.message_tracking_value'].findFromIdentifyingData({ id: 6 }));
    assert.ok(message);
    assert.strictEqual(this.env.models['mail.message'].findFromIdentifyingData({ id: 11 }), message);
    assert.strictEqual(message.trackingValues[0].changedFieldAsString, "Total:");
    assert.strictEqual(message.trackingValues[0].newValueAsString, "1");
    assert.strictEqual(message.trackingValues[0].oldValueAsString, "0");
});

QUnit.test('model test of tracking value of type float: from non-0 to 0', async function (assert) {
    assert.expect(6);

    await this.start();
    const message = this.env.models['mail.message'].create({
        id: 11,
        trackingValues: insert({
            changedField: "Total",
            fieldType: "float",
            id: 6,
            newValue: 0,
            oldValue: 1,
        }),
    });
    assert.ok(this.env.models['mail.message_tracking_value'].findFromIdentifyingData({ id: 6 }));
    assert.ok(message);
    assert.strictEqual(this.env.models['mail.message'].findFromIdentifyingData({ id: 11 }), message);
    assert.strictEqual(message.trackingValues[0].changedFieldAsString, "Total:");
    assert.strictEqual(message.trackingValues[0].newValueAsString, "0.00");
    assert.strictEqual(message.trackingValues[0].oldValueAsString, "1.00");
});

QUnit.test('model test of tracking value of type float: from 0 to non-0', async function (assert) {
    assert.expect(6);

    await this.start();
    const message = this.env.models['mail.message'].create({
        id: 11,
        trackingValues: insert({
            changedField: "Total",
            fieldType: "float",
            id: 6,
            newValue: 1,
            oldValue: 0,
        }),
    });
    assert.ok(this.env.models['mail.message_tracking_value'].findFromIdentifyingData({ id: 6 }));
    assert.ok(message);
    assert.strictEqual(this.env.models['mail.message'].findFromIdentifyingData({ id: 11 }), message);
    assert.strictEqual(message.trackingValues[0].changedFieldAsString, "Total:");
    assert.strictEqual(message.trackingValues[0].newValueAsString, "1.00");
    assert.strictEqual(message.trackingValues[0].oldValueAsString, "0.00");
});

QUnit.test('model test of tracking value of type monetary: from non-0 to 0', async function (assert) {
    assert.expect(6);

    await this.start();
    const message = this.env.models['mail.message'].create({
        id: 11,
        trackingValues: insert({
            changedField: "Total",
            fieldType: "monetary",
            id: 6,
            newValue: 0,
            oldValue: 1,
        }),
    });
    assert.ok(this.env.models['mail.message_tracking_value'].findFromIdentifyingData({ id: 6 }));
    assert.ok(message);
    assert.strictEqual(this.env.models['mail.message'].findFromIdentifyingData({ id: 11 }), message);
    assert.strictEqual(message.trackingValues[0].changedFieldAsString, "Total:");
    assert.strictEqual(message.trackingValues[0].newValueAsString, "0.00");
    assert.strictEqual(message.trackingValues[0].oldValueAsString, "1.00");
});

QUnit.test('model test of tracking value of type monetary: from 0 to non-0', async function (assert) {
    assert.expect(6);

    await this.start();
    const message = this.env.models['mail.message'].create({
        id: 11,
        trackingValues: insert({
            changedField: "Total",
            fieldType: "monetary",
            id: 6,
            newValue: 1,
            oldValue: 0,
        }),
    });
    assert.ok(this.env.models['mail.message_tracking_value'].findFromIdentifyingData({ id: 6 }));
    assert.ok(message);
    assert.strictEqual(this.env.models['mail.message'].findFromIdentifyingData({ id: 11 }), message);
    assert.strictEqual(message.trackingValues[0].changedFieldAsString, "Total:");
    assert.strictEqual(message.trackingValues[0].newValueAsString, "1.00");
    assert.strictEqual(message.trackingValues[0].oldValueAsString, "0.00");
});

QUnit.test('model test of tracking value of type boolean: from true to false', async function (assert) {
    assert.expect(6);
    await this.start();
    const message = this.env.models['mail.message'].create({
        id: 11,
        trackingValues: insert({
            changedField: "Is Ready",
            fieldType: "boolean",
            id: 6,
            newValue: false,
            oldValue: true,
        }),
    });
    assert.ok(this.env.models['mail.message_tracking_value'].findFromIdentifyingData({ id: 6 }));
    assert.ok(message);
    assert.strictEqual(this.env.models['mail.message'].findFromIdentifyingData({ id: 11 }), message);
    assert.strictEqual(message.trackingValues[0].changedFieldAsString, "Is Ready:");
    assert.strictEqual(message.trackingValues[0].newValueAsString, "False");
    assert.strictEqual(message.trackingValues[0].oldValueAsString, "True");
});

QUnit.test('model test of tracking value of type boolean: from false to true', async function (assert) {
    assert.expect(6);

    await this.start();
    const message = this.env.models['mail.message'].create({
        id: 11,
        trackingValues: insert({
            changedField: "Is Ready",
            fieldType: "boolean",
            id: 6,
            newValue: true,
            oldValue: false,
        }),
    });
    assert.ok(this.env.models['mail.message_tracking_value'].findFromIdentifyingData({ id: 6 }));
    assert.ok(message);
    assert.strictEqual(this.env.models['mail.message'].findFromIdentifyingData({ id: 11 }), message);
    assert.strictEqual(message.trackingValues[0].changedFieldAsString, "Is Ready:");
    assert.strictEqual(message.trackingValues[0].newValueAsString, "True");
    assert.strictEqual(message.trackingValues[0].oldValueAsString, "False");
});

QUnit.test('model test of tracking value of type char: from a string to empty string', async function (assert) {
    assert.expect(6);

    await this.start();
    const message = this.env.models['mail.message'].create({
        id: 11,
        trackingValues: insert({
            changedField: "Name",
            fieldType: "char",
            id: 6,
            newValue: "",
            oldValue: "Marc",
        }),
    });
    assert.ok(this.env.models['mail.message_tracking_value'].findFromIdentifyingData({ id: 6 }));
    assert.ok(message);
    assert.strictEqual(this.env.models['mail.message'].findFromIdentifyingData({ id: 11 }), message);
    assert.strictEqual(message.trackingValues[0].changedFieldAsString, "Name:");
    assert.strictEqual(message.trackingValues[0].newValueAsString, "");
    assert.strictEqual(message.trackingValues[0].oldValueAsString, "Marc");
});

QUnit.test('model test of tracking value of type char: from empty string to a string', async function (assert) {
    assert.expect(6);

    await this.start();
    const message = this.env.models['mail.message'].create({
        id: 11,
        trackingValues: insert({
            changedField: "Name",
            fieldType: "char",
            id: 6,
            newValue: "Marc",
            oldValue: "",
        }),
    });
    assert.ok(this.env.models['mail.message_tracking_value'].findFromIdentifyingData({ id: 6 }));
    assert.ok(message);
    assert.strictEqual(this.env.models['mail.message'].findFromIdentifyingData({ id: 11 }), message);
    assert.strictEqual(message.trackingValues[0].changedFieldAsString, "Name:");
    assert.strictEqual(message.trackingValues[0].newValueAsString, "Marc");
    assert.strictEqual(message.trackingValues[0].oldValueAsString, "");
});

QUnit.test('model test of tracking value of type date: from no date to a set date', async function (assert) {
    assert.expect(6);
    await this.start();

    const message = this.env.models['mail.message'].create({
        id: 11,
        trackingValues: insert({
            changedField: "Deadline",
            fieldType: "date",
            id: 6,
            newValue: "2018-12-14",
            oldValue: false,
        }),
    });
    assert.ok(this.env.models['mail.message_tracking_value'].findFromIdentifyingData({ id: 6 }));
    assert.ok(message);
    assert.strictEqual(this.env.models['mail.message'].findFromIdentifyingData({ id: 11 }), message);
    assert.strictEqual(message.trackingValues[0].changedFieldAsString, "Deadline:");
    assert.strictEqual(message.trackingValues[0].newValueAsString, "12/14/2018");
    assert.strictEqual(message.trackingValues[0].oldValueAsString, "");
});

QUnit.test('model test of tracking value of type date: from a set date to no date', async function (assert) {
    assert.expect(6);
    await this.start();
    const message = this.env.models['mail.message'].create({
        id: 11,
        trackingValues: insert({
            changedField: "Deadline",
            fieldType: "date",
            id: 6,
            newValue: false,
            oldValue: "2018-12-14",
        }),
    });
    assert.ok(this.env.models['mail.message_tracking_value'].findFromIdentifyingData({ id: 6 }));
    assert.ok(message);
    assert.strictEqual(this.env.models['mail.message'].findFromIdentifyingData({ id: 11 }), message);
    assert.strictEqual(message.trackingValues[0].changedFieldAsString, "Deadline:");
    assert.strictEqual(message.trackingValues[0].newValueAsString, "");
    assert.strictEqual(message.trackingValues[0].oldValueAsString, "12/14/2018");
});

QUnit.test('model test of tracking value of type datetime: from no date and time to a set date and time', async function (assert) {
    assert.expect(6);
    await this.start();
    const message = this.env.models['mail.message'].create({
        id: 11,
        trackingValues: insert({
            changedField: "Deadline",
            fieldType: "datetime",
            id: 6,
            newValue: "2018-12-14 13:42:28",
            oldValue: false,
        }),
    });
    assert.ok(this.env.models['mail.message_tracking_value'].findFromIdentifyingData({ id: 6 }));
    assert.ok(message);
    assert.strictEqual(this.env.models['mail.message'].findFromIdentifyingData({ id: 11 }), message);
    assert.strictEqual(message.trackingValues[0].changedFieldAsString, "Deadline:");
    assert.strictEqual(message.trackingValues[0].newValueAsString, "12/14/2018 13:42:28");
    assert.strictEqual(message.trackingValues[0].oldValueAsString, "");
});

QUnit.test('model test of tracking value of type datetime: from a set date and time to no date and time', async function (assert) {
    assert.expect(6);
    await this.start();
    const message = this.env.models['mail.message'].create({
        id: 11,
        trackingValues: insert({
            changedField: "Deadline",
            fieldType: "datetime",
            id: 6,
            newValue: false,
            oldValue: "2018-12-14 13:42:28",
        }),
    });
    assert.ok(this.env.models['mail.message_tracking_value'].findFromIdentifyingData({ id: 6 }));
    assert.ok(message);
    assert.strictEqual(this.env.models['mail.message'].findFromIdentifyingData({ id: 11 }), message);
    assert.strictEqual(message.trackingValues[0].changedFieldAsString, "Deadline:");
    assert.strictEqual(message.trackingValues[0].newValueAsString, "");
    assert.strictEqual(message.trackingValues[0].oldValueAsString, "12/14/2018 13:42:28");
});

QUnit.test('model test of tracking value of type text: from some text to empty', async function (assert) {
    assert.expect(6);
    await this.start();
    const message = this.env.models['mail.message'].create({
        id: 11,
        trackingValues: insert({
            changedField: "Name",
            fieldType: "text",
            id: 6,
            newValue: "",
            oldValue: "Marc",
        }),
    });
    assert.ok(this.env.models['mail.message_tracking_value'].findFromIdentifyingData({ id: 6 }));
    assert.ok(message);
    assert.strictEqual(this.env.models['mail.message'].findFromIdentifyingData({ id: 11 }), message);
    assert.strictEqual(message.trackingValues[0].changedFieldAsString, "Name:");
    assert.strictEqual(message.trackingValues[0].newValueAsString, "");
    assert.strictEqual(message.trackingValues[0].oldValueAsString, "Marc");
});

QUnit.test('model test of tracking value of type text: from empty to some text', async function (assert) {
    assert.expect(6);
    await this.start();
    const message = this.env.models['mail.message'].create({
        id: 11,
        trackingValues: insert({
            changedField: "Name",
            fieldType: "text",
            id: 6,
            newValue: "Marc",
            oldValue: "",
        }),
    });
    assert.ok(this.env.models['mail.message_tracking_value'].findFromIdentifyingData({ id: 6 }));
    assert.ok(message);
    assert.strictEqual(this.env.models['mail.message'].findFromIdentifyingData({ id: 11 }), message);
    assert.strictEqual(message.trackingValues[0].changedFieldAsString, "Name:");
    assert.strictEqual(message.trackingValues[0].newValueAsString, "Marc");
    assert.strictEqual(message.trackingValues[0].oldValueAsString, "");
});

QUnit.test('model test of tracking value of type selection: from a selection to no selection', async function (assert) {
    assert.expect(6);

    await this.start();
    const message = this.env.models['mail.message'].create({
        id: 11,
        trackingValues: insert({
            changedField: "State",
            fieldType: "selection",
            id: 6,
            newValue: "",
            oldValue: "ok",
        }),
    });
    assert.ok(this.env.models['mail.message_tracking_value'].findFromIdentifyingData({ id: 6 }));
    assert.ok(message);
    assert.strictEqual(this.env.models['mail.message'].findFromIdentifyingData({ id: 11 }), message);
    assert.strictEqual(message.trackingValues[0].changedFieldAsString, "State:");
    assert.strictEqual(message.trackingValues[0].newValueAsString, "");
    assert.strictEqual(message.trackingValues[0].oldValueAsString, "ok");
});

QUnit.test('model test of tracking value of type selection: from no selection to a selection', async function (assert) {
    assert.expect(6);

    await this.start();
    const message = this.env.models['mail.message'].create({
        id: 11,
        trackingValues: insert({
            changedField: "State",
            fieldType: "selection",
            id: 6,
            newValue: "ok",
            oldValue: "",
        }),
    });
    assert.ok(this.env.models['mail.message_tracking_value'].findFromIdentifyingData({ id: 6 }));
    assert.ok(message);
    assert.strictEqual(this.env.models['mail.message'].findFromIdentifyingData({ id: 11 }), message);
    assert.strictEqual(message.trackingValues[0].changedFieldAsString, "State:");
    assert.strictEqual(message.trackingValues[0].newValueAsString, "ok");
    assert.strictEqual(message.trackingValues[0].oldValueAsString, "");
});

QUnit.test('model test of tracking value of type many2one: from having a related record to no related record', async function (assert) {
    assert.expect(6);

    await this.start();
    const message = this.env.models['mail.message'].create({
        id: 11,
        trackingValues: insert({
            changedField: "Author",
            fieldType: "many2one",
            id: 6,
            newValue: "",
            oldValue: "Marc",
        }),
    });
    assert.ok(this.env.models['mail.message_tracking_value'].findFromIdentifyingData({ id: 6 }));
    assert.ok(message);
    assert.strictEqual(this.env.models['mail.message'].findFromIdentifyingData({ id: 11 }), message);
    assert.strictEqual(message.trackingValues[0].changedFieldAsString, "Author:");
    assert.strictEqual(message.trackingValues[0].newValueAsString, "");
    assert.strictEqual(message.trackingValues[0].oldValueAsString, "Marc");
});

QUnit.test('model test of tracking value of type many2one: from no related record to having a related record', async function (assert) {
    assert.expect(6);

    await this.start();
    const message = this.env.models['mail.message'].create({
        id: 11,
        trackingValues: insert({
            changedField: "Author",
            fieldType: "many2one",
            id: 6,
            newValue: "Marc",
            oldValue: "",
        }),
    });
    assert.ok(this.env.models['mail.message_tracking_value'].findFromIdentifyingData({ id: 6 }));
    assert.ok(message);
    assert.strictEqual(this.env.models['mail.message'].findFromIdentifyingData({ id: 11 }), message);
    assert.strictEqual(message.trackingValues[0].changedFieldAsString, "Author:");
    assert.strictEqual(message.trackingValues[0].newValueAsString, "Marc");
    assert.strictEqual(message.trackingValues[0].oldValueAsString, "");
});

QUnit.test('model test of tracking value (monetary type)', async function (assert) {
    assert.expect(6);

    await this.start({
        env: {
            session: {
                currencies: { 1: { symbol: '$', position: 'before' } },
            },
        },
    });
    const message = this.env.models['mail.message'].create({
        id: 11,
        trackingValues: insert({
            changedField: "Revenue",
            currencyId: 1,
            fieldType: "monetary",
            id: 6,
            newValue: 500,
            oldValue: 1000,
        }),
    });
    assert.ok(this.env.models['mail.message_tracking_value'].findFromIdentifyingData({ id: 6 }));
    assert.ok(message);
    assert.strictEqual(this.env.models['mail.message'].findFromIdentifyingData({ id: 11 }), message);
    assert.strictEqual(message.trackingValues[0].changedFieldAsString, "Revenue:");
    assert.strictEqual(message.trackingValues[0].newValueAsString, "$ 500.00");
    assert.strictEqual(message.trackingValues[0].oldValueAsString, "$ 1000.00");
});

});
});
});
