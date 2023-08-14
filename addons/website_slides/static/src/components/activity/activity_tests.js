odoo.define('website_slides/static/src/tests/activity_tests.js', function (require) {
'use strict';

const components = {
    Activity: require('mail/static/src/components/activity/activity.js'),
};

const {
    afterEach,
    beforeEach,
    createRootComponent,
    start,
} = require('mail/static/src/utils/test_utils.js');

QUnit.module('website_slides', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('activity', {}, function () {
QUnit.module('activity_tests.js', {
    beforeEach() {
        beforeEach(this);

        this.createActivityComponent = async activity => {
            await createRootComponent(this, components.Activity, {
                props: { activityLocalId: activity.localId },
                target: this.widget.el,
            });
        };

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

QUnit.test('grant course access', async function (assert) {
    assert.expect(8);

    await this.start({
        async mockRPC(route, args) {
            if (args.method === 'action_grant_access') {
                assert.strictEqual(args.args.length, 1);
                assert.strictEqual(args.args[0].length, 1);
                assert.strictEqual(args.args[0][0], 100);
                assert.strictEqual(args.kwargs.partner_id, 5);
                assert.step('access_grant');
            }
            return this._super(...arguments);
        },
    });
    const activity = this.env.models['mail.activity'].create({
        id: 100,
        canWrite: true,
        thread: [['insert', {
            id: 100,
            model: 'slide.channel',
        }]],
        requestingPartner: [['insert', {
            id: 5,
            displayName: "Pauvre pomme",
        }]],
        type: [['insert', {
            id: 1,
            displayName: "Access Request",
        }]],
    });
    await this.createActivityComponent(activity);

    assert.containsOnce(document.body, '.o_Activity', "should have activity component");
    assert.containsOnce(document.body, '.o_Activity_grantAccessButton', "should have grant access button");

    document.querySelector('.o_Activity_grantAccessButton').click();
    assert.verifySteps(['access_grant'], "Grant button should trigger the right rpc call");
});

QUnit.test('refuse course access', async function (assert) {
    assert.expect(8);

    await this.start({
        async mockRPC(route, args) {
            if (args.method === 'action_refuse_access') {
                assert.strictEqual(args.args.length, 1);
                assert.strictEqual(args.args[0].length, 1);
                assert.strictEqual(args.args[0][0], 100);
                assert.strictEqual(args.kwargs.partner_id, 5);
                assert.step('access_refuse');
            }
            return this._super(...arguments);
        },
    });
    const activity = this.env.models['mail.activity'].create({
        id: 100,
        canWrite: true,
        thread: [['insert', {
            id: 100,
            model: 'slide.channel',
        }]],
        requestingPartner: [['insert', {
            id: 5,
            displayName: "Pauvre pomme",
        }]],
        type: [['insert', {
            id: 1,
            displayName: "Access Request",
        }]],
    });
    await this.createActivityComponent(activity);

    assert.containsOnce(document.body, '.o_Activity', "should have activity component");
    assert.containsOnce(document.body, '.o_Activity_refuseAccessButton', "should have refuse access button");

    document.querySelector('.o_Activity_refuseAccessButton').click();
    assert.verifySteps(['access_refuse'], "refuse button should trigger the right rpc call");
});

});
});
});

});
