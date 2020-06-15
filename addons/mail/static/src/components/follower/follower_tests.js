odoo.define('mail/static/src/components/follower/follower_tests.js', function (require) {
'use strict';

const components = {
    Follower: require('mail/static/src/components/follower/follower.js'),
};
const {
    afterEach: utilsAfterEach,
    afterNextRender,
    beforeEach: utilsBeforeEach,
    start: utilsStart,
} = require('mail/static/src/utils/test_utils.js');

const Bus = require('web.Bus');

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('follower', {}, function () {
QUnit.module('follower_tests.js', {
    beforeEach() {
        utilsBeforeEach(this);

        this.createFollowerComponent = async (follower) => {
            const FollowerComponent = components.Follower;
            FollowerComponent.env = this.env;
            this.component = new FollowerComponent(null, { followerLocalId: follower.localId });
            await this.component.mount(this.widget.el);
        };

        this.start = async params => {
            let { env, widget } = await utilsStart(Object.assign({}, params, {
                data: this.data,
            }));
            this.env = env;
            this.widget = widget;
        };
    },
    afterEach() {
        utilsAfterEach(this);
        if (this.component) {
            this.component.destroy();
            this.component = undefined;
        }
        if (this.widget) {
            this.widget.destroy();
            this.widget = undefined;
        }
        this.env = undefined;
        delete components.Follower.env;
    },
});

QUnit.test('base rendering not editable', async function (assert) {
    assert.expect(5);

    await this.start({
        async mockRPC(route, args) {
            if (route === '/web/image/mail.channel/1/image_128') {
                return;
            }
            return this._super(...arguments);
        },
    });

    const thread = this.env.models['mail.thread'].create({
        id: 100,
        model: 'res.partner',
    });
    const follower = await this.env.models['mail.follower'].create({
        channel: [['insert', { id: 1, model: 'mail.channel', name: "François Perusse" }]],
        followedThread: [['link', thread]],
        id: 2,
        isActive: true,
        isEditable: false,
    });
    await this.createFollowerComponent(follower);
    assert.containsOnce(
        document.body,
        '.o_Follower',
        "should have follower component"
    );
    assert.containsOnce(
        document.body,
        '.o_Follower_details',
        "should display a details part"
    );
    assert.containsOnce(
        document.body,
        '.o_Follower_avatar',
        "should display the avatar of the follower"
    );
    assert.containsOnce(
        document.body,
        '.o_Follower_name',
        "should display the name of the follower"
    );
    assert.containsNone(
        document.body,
        '.o_Follower_button',
        "should have no button as follower is not editable"
    );
});

QUnit.test('base rendering editable', async function (assert) {
    assert.expect(6);

    await this.start({
        async mockRPC(route, args) {
            if (route === 'web/image/mail.channel/1/image_128') {
                return;
            }
            return this._super(...arguments);
        },
    });
    const thread = this.env.models['mail.thread'].create({
        id: 100,
        model: 'res.partner',
    });
    const follower = await this.env.models['mail.follower'].create({
        channel: [['insert', { id: 1, model: 'mail.channel', name: "François Perusse" }]],
        followedThread: [['link', thread]],
        id: 2,
        isActive: true,
        isEditable: true,
    });
    await this.createFollowerComponent(follower);
    assert.containsOnce(
        document.body,
        '.o_Follower',
        "should have follower component"
    );
    assert.containsOnce(
        document.body,
        '.o_Follower_details',
        "should display a details part"
    );
    assert.containsOnce(
        document.body,
        '.o_Follower_avatar',
        "should display the avatar of the follower"
    );
    assert.containsOnce(
        document.body,
        '.o_Follower_name',
        "should display the name of the follower"
    );
    assert.containsOnce(
        document.body,
        '.o_Follower_editButton',
        "should have an edit button"
    );
    assert.containsOnce(
        document.body,
        '.o_Follower_removeButton',
        "should have a remove button"
    );
});

QUnit.test('click on channel follower details', async function (assert) {
    assert.expect(7);

    const bus = new Bus();
    bus.on('do-action', null, payload => {
        assert.step('do_action');
        assert.strictEqual(
            payload.action.res_id,
            1,
            "The redirect action should redirect to the right res id (1)"
        );
        assert.strictEqual(
            payload.action.res_model,
            'mail.channel',
            "The redirect action should redirect to the right res model (mail.channel)"
        );
        assert.strictEqual(
            payload.action.type,
            "ir.actions.act_window",
            "The redirect action should be of type 'ir.actions.act_window'"
        );
    });

    await this.start({
        env: { bus },
        async mockRPC(route, args) {
            if (route === 'web/image/mail.channel/1/image_128') {
                return;
            }
            return this._super(...arguments);
        },
    });
    const thread = this.env.models['mail.thread'].create({
        id: 100,
        model: 'res.partner',
    });
    const follower = await this.env.models['mail.follower'].create({
        channel: [['insert', { id: 1, model: 'mail.channel', name: "channel" }]],
        followedThread: [['link', thread]],
        id: 2,
        isActive: true,
        isEditable: true,
    });
    await this.createFollowerComponent(follower);
    assert.containsOnce(
        document.body,
        '.o_Follower',
        "should have follower component"
    );
    assert.containsOnce(
        document.body,
        '.o_Follower_details',
        "should display a details part"
    );

    document.querySelector('.o_Follower_details').click();
    assert.verifySteps(
        ['do_action'],
        "clicking on channel should redirect to channel form view"
    );
});

QUnit.test('click on partner follower details', async function (assert) {
    assert.expect(7);

    const bus = new Bus();
    bus.on('do-action', null, payload => {
        assert.step('do_action');
        assert.strictEqual(
            payload.action.res_id,
            3,
            "The redirect action should redirect to the right res id (3)"
        );
        assert.strictEqual(
            payload.action.res_model,
            'res.partner',
            "The redirect action should redirect to the right res model (res.partner)"
        );
        assert.strictEqual(
            payload.action.type,
            "ir.actions.act_window",
            "The redirect action should be of type 'ir.actions.act_window'"
        );
    });

    await this.start({
        env: { bus },
        async mockRPC(route, args) {
            if (route === 'web/image/res.partner/3/image_128') {
                return;
            }
            return this._super(...arguments);
        },
    });
    const thread = this.env.models['mail.thread'].create({
        id: 100,
        model: 'res.partner',
    });
    const follower = await this.env.models['mail.follower'].create({
        followedThread: [['link', thread]],
        id: 2,
        isActive: true,
        isEditable: true,
        partner: [['insert', {
            email: "bla@bla.bla",
            id: this.env.session.partner_id,
            name: "François Perusse",
        }]],
    });
    await this.createFollowerComponent(follower);
    assert.containsOnce(
        document.body,
        '.o_Follower',
        "should have follower component"
    );
    assert.containsOnce(
        document.body,
        '.o_Follower_details',
        "should display a details part"
    );

    document.querySelector('.o_Follower_details').click();
    assert.verifySteps(
        ['do_action'],
        "clicking on follower should redirect to partner form view"
    );
});

QUnit.test('click on edit follower', async function (assert) {
    assert.expect(5);

    await this.start({
        hasDialog: true,
        async mockRPC(route, args) {
            if (route === 'web/image/res.partner/3/image_128') {
                return;
            }
            if (route.includes('/mail/read_subscription_data')) {
                assert.step('fetch_subtypes');
                return [{
                    default: true,
                    followed: true,
                    internal: false,
                    id: 1,
                    name: "Dummy test",
                    res_model: 'res.partner'
                }];
            }
            return this._super(...arguments);
        },
    });
    const thread = this.env.models['mail.thread'].create({
        id: 100,
        model: 'res.partner',
    });
    const follower = await this.env.models['mail.follower'].create({
        followedThread: [['link', thread]],
        id: 2,
        isActive: true,
        isEditable: true,
        partner: [['insert', {
            email: "bla@bla.bla",
            id: this.env.session.partner_id,
            name: "François Perusse",
        }]],
    });
    await this.createFollowerComponent(follower);
    assert.containsOnce(
        document.body,
        '.o_Follower',
        "should have follower component"
    );
    assert.containsOnce(
        document.body,
        '.o_Follower_editButton',
        "should display an edit button"
    );

    await afterNextRender(() => document.querySelector('.o_Follower_editButton').click());
    assert.verifySteps(
        ['fetch_subtypes'],
        "clicking on edit follower should fetch subtypes"
    );

    assert.containsOnce(
        document.body,
        '.o_FollowerSubtypeList',
        "A dialog allowing to edit follower subtypes should have been created"
    );
});

});
});
});

});
