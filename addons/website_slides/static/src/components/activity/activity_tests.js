odoo.define('website_slides/static/src/components/activity/activity_tests.js', function (require) {
'use strict';

const components = {
    Activity: require('mail/static/src/components/activity/activity.js'),
};

const {
    afterEach,
    beforeEach,
    start,
} = require('mail/static/src/utils/test_utils.js');

QUnit.module('website_slides', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('activity', {}, function () {
QUnit.module('activity_tests.js', {
    beforeEach() {
        beforeEach(this);

        this.createActivityComponent = async activity => {
            const ActivityComponent = components.Activity;
            ActivityComponent.env = this.env;
            this.component = new ActivityComponent(null, {
                activityLocalId: activity.localId,
            });
            await this.component.mount(this.widget.el);
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
    assert.expect(7);

    await this.start({
        async mockRPC(route, args) {
            if (args.method === 'action_grant_access') {
                assert.strictEqual(args.args.length, 2);
                assert.strictEqual(args.args[0], 100);
                assert.strictEqual(args.args[1], 5);
                assert.step('access_grant');
            }
            return this._super(...arguments);
        },
    });
    const activity = this.env.models['mail.activity'].create({
        canWrite: true,
        assignee: [['insert', {
            id: this.env.session.uid,
            partnerDisplayName: "Eden Hazard",
        }]],
        res_id: 100,
        creator: [['insert', {
            id: 7,
            partnerDisplayName: "Pauvre pomme",
        }]],
        creatorPartner: [['insert', {
            id: 5,
            partnerDisplayName: "Pauvre pomme",
        }]],
        type: [['insert', {
            id: 1,
            displayName: "Access Request",
        }]],
    });
    await this.createActivityComponent(activity);

    assert.containsOnce(document.body, '.o_Activity', "should have activity component");
    assert.containsOnce(document.body, '.o_Activity_GrantAccessButton', "should have grant access button");

    document.querySelector('.o_Activity_GrantAccessButton').click();
    assert.verifySteps(['access_grant'], "Grant button should trigger the right rpc call");
});

QUnit.test('refuse course access', async function (assert) {
    assert.expect(7);

    await this.start({
        async mockRPC(route, args) {
            if (args.method === 'action_refuse_access') {
                assert.strictEqual(args.args.length, 2);
                assert.strictEqual(args.args[0], 100);
                assert.strictEqual(args.args[1], 5);
                assert.step('access_refuse');
            }
            return this._super(...arguments);
        },
    });
    const activity = this.env.models['mail.activity'].create({
        canWrite: true,
        assignee: [['insert', {
            id: this.env.session.uid,
            partnerDisplayName: "Eden Hazard",
        }]],
        res_id: 100,
        creator: [['insert', {
            id: 7,
            partnerDisplayName: "Pauvre pomme",
        }]],
        creatorPartner: [['insert', {
            id: 5,
            partnerDisplayName: "Pauvre pomme",
        }]],
        type: [['insert', {
            id: 1,
            displayName: "Access Request",
        }]],
    });
    await this.createActivityComponent(activity);

    assert.containsOnce(document.body, '.o_Activity', "should have activity component");
    assert.containsOnce(document.body, '.o_Activity_RefuseAccessButton', "should have refuse access button");

    document.querySelector('.o_Activity_RefuseAccessButton').click();
    assert.verifySteps(['access_refuse'], "refuse button should trigger the right rpc call");
});

});
});
});

});
