odoo.define('mail/static/src/components/follower_list_menu/follower_list_menu_tests.js', function (require) {
'use strict';

const components = {
    FollowerListMenu: require('mail/static/src/components/follower_list_menu/follower_list_menu.js'),
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
QUnit.module('follower_list_menu', {}, function () {
QUnit.module('follower_list_menu_tests.js', {
    beforeEach() {
        utilsBeforeEach(this);

        this.createFollowerListMenuComponent = async (thread, otherProps = {}) => {
            const FollowerListMenuComponent = components.FollowerListMenu;
            FollowerListMenuComponent.env = this.env;
            this.component = new FollowerListMenuComponent(null,
                Object.assign(otherProps, { threadLocalId: thread.localId })
            );
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
        delete components.FollowerListMenu.env;
    },
});

QUnit.test('base rendering not editable', async function (assert) {
    assert.expect(5);

    await this.start();
    const thread = this.env.models['mail.thread'].create({
        id: 100,
        model: 'res.partner',
    });
    await this.createFollowerListMenuComponent(thread, { isDisabled: true });
    assert.containsOnce(
        document.body,
        '.o_FollowerListMenu',
        "should have followers menu component"
    );
    assert.containsOnce(
        document.body,
        '.o_FollowerListMenu_buttonFollowers',
        "should have followers button"
    );
    assert.ok(
        document.querySelector('.o_FollowerListMenu_buttonFollowers').disabled,
        "followers button should be disabled"
    );
    assert.containsNone(
        document.body,
        '.o_FollowerListMenu_dropdown',
        "followers dropdown should not be opened"
    );

    document.querySelector('.o_FollowerListMenu_buttonFollowers').click();
    assert.containsNone(
        document.body,
        '.o_FollowerListMenu_dropdown',
        "followers dropdown should still be closed as button is disabled"
    );
});

QUnit.test('base rendering editable', async function (assert) {
    assert.expect(5);

    await this.start();
    const thread = this.env.models['mail.thread'].create({
        id: 100,
        model: 'res.partner',
    });
    await this.createFollowerListMenuComponent(thread);

    assert.containsOnce(
        document.body,
        '.o_FollowerListMenu',
        "should have followers menu component"
    );
    assert.containsOnce(
        document.body,
        '.o_FollowerListMenu_buttonFollowers',
        "should have followers button"
    );
    assert.notOk(
        document.querySelector('.o_FollowerListMenu_buttonFollowers').disabled,
        "followers button should not be disabled"
    );
    assert.containsNone(
        document.body,
        '.o_FollowerListMenu_dropdown',
        "followers dropdown should not be opened"
    );

    await afterNextRender(() => {
        document.querySelector('.o_FollowerListMenu_buttonFollowers').click();
    });
    assert.containsOnce(
        document.body,
        '.o_FollowerListMenu_dropdown',
        "followers dropdown should be opened"
    );
});

QUnit.test('click on "add followers" button', async function (assert) {
    assert.expect(18);

    const followerIds = [];
    const bus = new Bus();
    bus.on('do-action', null, payload => {
        assert.step('action:open_view');
        assert.strictEqual(
            payload.action.context.default_res_model,
            'res.partner',
            "'The 'add followers' action should contain thread model in context'"
        );
        assert.notOk(
            payload.action.context.mail_invite_follower_channel_only,
            "The 'add followers' action should not be restricted to channels only"
        );
        assert.strictEqual(
            payload.action.context.default_res_id,
            100,
            "The 'add followers' action should contain thread id in context"
        );
        assert.strictEqual(
            payload.action.res_model,
            'mail.wizard.invite',
            "The 'add followers' action should be a wizard invite of mail module"
        );
        assert.strictEqual(
            payload.action.type,
            "ir.actions.act_window",
            "The 'add followers' action should be of type 'ir.actions.act_window'"
        );
        followerIds.push(1);
        payload.options.on_close();
    });

    await this.start({
        env: { bus },
        async mockRPC(route, args) {
            if (route.includes('web/image/')) {
                return;
            } else if (route.includes('res.partner/read')) {
                assert.step('rpc:read_follower_ids');
                return [{
                    id: 100,
                    message_follower_ids: followerIds,
                }];
            } else if (route.includes('mail/read_followers')) {
                assert.step('rpc:read_followers_details');
                return {
                    followers: [{
                        partner_id: 42,
                        email: "bla@bla.bla",
                        id: 1,
                        is_active: true,
                        is_editable: true,
                        name: "François Perusse",
                    }]
                };
            }
            return this._super(...arguments);
        },
    });
    const thread = this.env.models['mail.thread'].create({
        id: 100,
        model: 'res.partner',
    });
    await this.createFollowerListMenuComponent(thread);

    assert.containsOnce(
        document.body,
        '.o_FollowerListMenu',
        "should have followers menu component"
    );
    assert.containsOnce(
        document.body,
        '.o_FollowerListMenu_buttonFollowers',
        "should have followers button"
    );
    assert.strictEqual(
        document.querySelector('.o_FollowerListMenu_buttonFollowersCount').textContent,
        "0",
        "Followers counter should be equal to 0"
    );

    await afterNextRender(() => {
        document.querySelector('.o_FollowerListMenu_buttonFollowers').click();
    });
    assert.containsOnce(
        document.body,
        '.o_FollowerListMenu_dropdown',
        "followers dropdown should be opened"
    );
    assert.containsOnce(
        document.body,
        '.o_FollowerListMenu_addFollowersButton',
        "followers dropdown should contain a 'Add followers' button"
    );

    await afterNextRender(() => {
        document.querySelector('.o_FollowerListMenu_addFollowersButton').click();
    });
    assert.containsNone(
        document.body,
        '.o_FollowerListMenu_dropdown',
        "followers dropdown should be closed after click on 'Add followers'"
    );
    assert.verifySteps([
        'action:open_view',
        'rpc:read_follower_ids',
        'rpc:read_followers_details',
    ]);
    assert.strictEqual(
        document.querySelector('.o_FollowerListMenu_buttonFollowersCount').textContent,
        "1",
        "Followers counter should now be equal to 1"
    );

    await afterNextRender(() => {
        document.querySelector('.o_FollowerListMenu_buttonFollowers').click();
    });
    assert.containsOnce(
        document.body,
        '.o_FollowerMenu_follower',
        "Follower list should be refreshed and contain a follower"
    );
    assert.strictEqual(
        document.querySelector('.o_Follower_name').textContent,
        "François Perusse",
        "Follower added in follower list should be the one added"
    );
});

QUnit.test('click on "add channels" button', async function (assert) {
    assert.expect(18);

    const followerIds = [];
    const bus = new Bus();
    bus.on('do-action', null, payload => {
        assert.step('action:open_view');
        assert.strictEqual(
            payload.action.context.default_res_model,
            'res.partner',
            "'The 'add channels' action should contain thread model in context'"
        );
        assert.ok(
            payload.action.context.mail_invite_follower_channel_only,
            "The 'add channels' action should be restricted to channels only"
        );
        assert.strictEqual(
            payload.action.context.default_res_id,
            100,
            "The 'add channels' action should contain thread id in context"
        );
        assert.strictEqual(
            payload.action.res_model,
            'mail.wizard.invite',
            "The 'add channels' action should be a wizard invite of mail module"
        );
        assert.strictEqual(
            payload.action.type,
            "ir.actions.act_window",
            "The 'add channels' action should be of type 'ir.actions.act_window'"
        );
        followerIds.push(1);
        payload.options.on_close();
    });
    await this.start({
        env: { bus },
        async mockRPC(route, args) {
            if (route.includes('web/image/')) {
                return;
            } else if (route.includes('res.partner/read')) {
                assert.step('rpc:read_follower_ids');
                return [{
                    id: 100,
                    message_follower_ids: followerIds,
                }];
            } else if (route.includes('mail/read_followers')) {
                assert.step('rpc:read_followers_details');
                return {
                    followers: [{
                        channel_id: 42,
                        email: "bla@bla.bla",
                        id: 1,
                        is_active: true,
                        is_editable: true,
                        name: "Supa channel",
                    }]
                };
            }
            return this._super(...arguments);
        },
    });
    const thread = this.env.models['mail.thread'].create({
        id: 100,
        model: 'res.partner',
    });
    await this.createFollowerListMenuComponent(thread);

    assert.containsOnce(
        document.body,
        '.o_FollowerListMenu',
        "should have followers menu component"
    );
    assert.strictEqual(
        document.querySelector('.o_FollowerListMenu_buttonFollowersCount').textContent,
        "0",
        "Followers counter should be equal to 0"
    );
    assert.containsOnce(
        document.body,
        '.o_FollowerListMenu_buttonFollowers',
        "should have followers button"
    );

    await afterNextRender(() => {
        document.querySelector('.o_FollowerListMenu_buttonFollowers').click();
    });
    assert.containsOnce(
        document.body,
        '.o_FollowerListMenu_dropdown',
        "followers dropdown should be opened"
    );
    assert.containsOnce(
        document.body,
        '.o_FollowerListMenu_addChannelsButton',
        "followers dropdown should contain a 'Add channels' button"
    );

    await afterNextRender(() => {
        document.querySelector('.o_FollowerListMenu_addChannelsButton').click();
    });
    assert.containsNone(
        document.body,
        '.o_FollowerListMenu_dropdown',
        "followers dropdown should be closed after click on 'add channels'"
    );
    assert.verifySteps([
        'action:open_view',
        'rpc:read_follower_ids',
        'rpc:read_followers_details',
    ]);
    assert.strictEqual(
        document.querySelector('.o_FollowerListMenu_buttonFollowersCount').textContent,
        "1",
        "Followers counter should now be equal to 1"
    );

    await afterNextRender(() => {
        document.querySelector('.o_FollowerListMenu_buttonFollowers').click();
    });
    assert.containsOnce(
        document.body,
        '.o_FollowerMenu_follower',
        "Follower list should be refreshed and contain a follower"
    );
    assert.strictEqual(
        document.querySelector('.o_Follower_name').textContent,
        "Supa channel",
        "Follower added in follower list should be the one added"
    );
});

QUnit.test('click on remove follower', async function (assert) {
    assert.expect(6);

    const self = this;
    await this.start({
        async mockRPC(route, args) {
            if (route.includes('web/image/')) {
                return;
            } else if (route.includes('message_unsubscribe')) {
                assert.step('message_unsubscribe');
                // FIXME "integration" test, should be replaced ... maybe by a tour.
                assert.deepEqual(
                    args.args,
                    [[100],[self.env.session.partner_id]],
                    "message unsubscribe should be called with right argument"
                );
                return;
            }
            return this._super(...arguments);
        },
    });
    const thread = this.env.models['mail.thread'].create({
        id: 100,
        model: 'res.partner',
    });
    await this.env.models['mail.follower'].create({
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
    await this.createFollowerListMenuComponent(thread);

    await afterNextRender(() => {
        document.querySelector('.o_FollowerListMenu_buttonFollowers').click();
    });
    assert.containsOnce(
        document.body,
        '.o_Follower',
        "should have follower component"
    );
    assert.containsOnce(
        document.body,
        '.o_Follower_removeButton',
        "should display a remove button"
    );

    await afterNextRender(() => {
        document.querySelector('.o_Follower_removeButton').click();
    });
    assert.verifySteps(
        ['message_unsubscribe'],
        "clicking on remove button should call 'message_unsubscribe' route"
    );
    assert.containsNone(
        document.body,
        '.o_Follower',
        "should no more have follower component"
    );
});

});
});
});

});
