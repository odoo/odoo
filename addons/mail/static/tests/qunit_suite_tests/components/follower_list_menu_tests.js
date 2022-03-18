/** @odoo-module **/

import { insert, link } from '@mail/model/model_field_command';
import {
    afterNextRender,
    createRootMessagingComponent,
    start,
    startServer,
} from '@mail/../tests/helpers/test_utils';

import Bus from 'web.Bus';

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('follower_list_menu_tests.js', {
    beforeEach() {
        this.createFollowerListMenuComponent = async (thread, target, otherProps = {}) => {
            const props = Object.assign({ threadLocalId: thread.localId }, otherProps);
            await createRootMessagingComponent(thread.env, "FollowerListMenu", {
                props,
                target,
            });
        };
    },
});

QUnit.test('base rendering not editable', async function (assert) {
    assert.expect(5);

    const { messaging, widget } = await start();
    const thread = messaging.models['Thread'].create({
        id: 100,
        model: 'res.partner',
    });
    await this.createFollowerListMenuComponent(thread, widget.el, { isDisabled: true });
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

    const { messaging, widget } = await start();
    const thread = messaging.models['Thread'].create({
        id: 100,
        model: 'res.partner',
        hasWriteAccess: true,
    });
    await this.createFollowerListMenuComponent(thread, widget.el);

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
    assert.expect(15);

    const pyEnv = await startServer();
    const [resPartnerId1, resPartnerId2] = pyEnv['res.partner'].create([
        { name: 'resPartner1'},
        { name: 'resPartner2' },
    ]);
    const mailFollowerId1 = pyEnv['mail.followers'].create({
        partner_id: resPartnerId2,
        email: "bla@bla.bla",
        is_active: true,
        name: "François Perusse",
        res_id: resPartnerId1,
        res_model: 'res.partner',
    });
    const bus = new Bus();
    bus.on('do-action', null, payload => {
        assert.step('action:open_view');
        assert.strictEqual(
            payload.action.context.default_res_model,
            'res.partner',
            "'The 'add followers' action should contain thread model in context'"
        );
        assert.strictEqual(
            payload.action.context.default_res_id,
            resPartnerId1,
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
        pyEnv['res.partner'].write([payload.action.context.default_res_id], { message_follower_ids: [mailFollowerId1] });
        payload.options.on_close();
    });
    const { messaging, widget } = await start({ env: { bus } });
    const thread = messaging.models['Thread'].create({
        hasWriteAccess: true,
        id: resPartnerId1,
        model: 'res.partner',
    });
    await this.createFollowerListMenuComponent(thread, widget.el);

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

QUnit.test('click on remove follower', async function (assert) {
    assert.expect(6);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create();
    const { messaging, widget } = await start({
        async mockRPC(route, args) {
            if (route.includes('message_unsubscribe')) {
                assert.step('message_unsubscribe');
                assert.deepEqual(
                    args.args,
                    [[resPartnerId1], [messaging.currentPartner.id]],
                    "message_unsubscribe should be called with right argument"
                );
            }
            return this._super(...arguments);
        },
    });
    const thread = messaging.models['Thread'].create({
        id: resPartnerId1,
        model: 'res.partner',
    });
    await messaging.models['Follower'].create({
        followedThread: link(thread),
        id: 2,
        isActive: true,
        partner: insert({
            email: "bla@bla.bla",
            id: messaging.currentPartner.id,
            name: "François Perusse",
        }),
    });
    await this.createFollowerListMenuComponent(thread, widget.el);

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
        "should no longer have follower component"
    );
});

QUnit.test('Hide "Add follower" and subtypes edition/removal buttons except own user on read only record', async function (assert) {
    assert.expect(5);

    const pyEnv = await startServer();
    const [resPartnerId1, resPartnerId2] = pyEnv['res.partner'].create([{ name: "resPartner1" }, { name: "resPartner2" }]);
    pyEnv['mail.followers'].create([
        {
            name: "Jean Michang",
            is_active: true,
            partner_id: pyEnv.currentPartnerId,
            res_id: resPartnerId1,
            res_model: 'res.partner',
        },
        {
            name: "Eden Hazard",
            is_active: true,
            partner_id: resPartnerId2,
            res_id: resPartnerId1,
            res_model: 'res.partner',
        },
    ]);
    const { click, createChatterContainerComponent } = await start({
        async mockRPC(route, args) {
            if (route === '/mail/thread/data') {
                // mimic user with no write access
                const res = await this._super(...arguments);
                res['hasWriteAccess'] = false;
                return res;
            }
            return this._super(...arguments);
        },
    });
    await createChatterContainerComponent({
        threadId: resPartnerId1,
        threadModel: 'res.partner',
    });

    await click('.o_FollowerListMenu_buttonFollowers');
    assert.containsNone(
        document.body,
        '.o_FollowerListMenu_addFollowersButton',
        "'Add followers' button should not be displayed for a readonly record",
    );
    const followersList = document.querySelectorAll('.o_Follower');
    assert.containsOnce(
        followersList[0],
        '.o_Follower_editButton',
        "should display edit button for a follower related to current user",
    );
    assert.containsOnce(
        followersList[0],
        '.o_Follower_removeButton',
        "should display remove button for a follower related to current user",
    );
    assert.containsNone(
        followersList[1],
        '.o_Follower_editButton',
        "should not display edit button for other followers on a readonly record",
    );
    assert.containsNone(
        followersList[1],
        '.o_Follower_removeButton',
        "should not display remove button for others on a readonly record",
    );
});

QUnit.test('Show "Add follower" and subtypes edition/removal buttons on all followers if user has write access', async function (assert) {
    assert.expect(5);

    const pyEnv = await startServer();
    const [resPartnerId1, resPartnerId2] = pyEnv['res.partner'].create([{ name: "resPartner1" }, { name: "resPartner2" }]);
    pyEnv['mail.followers'].create([
        {
            name: "Jean Michang",
            is_active: true,
            partner_id: pyEnv.currentPartnerId,
            res_id: resPartnerId1,
            res_model: 'res.partner',
        },
        {
            name: "Eden Hazard",
            is_active: true,
            partner_id: resPartnerId2,
            res_id: resPartnerId1,
            res_model: 'res.partner',
        },
    ]);
    const { click, createChatterContainerComponent } = await start({
        async mockRPC(route, args) {
            if (route === '/mail/thread/data') {
                // mimic user with write access
                const res = await this._super(...arguments);
                res['hasWriteAccess'] = true;
                return res;
            }
            return this._super(...arguments);
        },
    });
    await createChatterContainerComponent({
        threadId: resPartnerId1,
        threadModel: 'res.partner',
    });

    await click('.o_FollowerListMenu_buttonFollowers');
    assert.containsOnce(
        document.body,
        '.o_FollowerListMenu_addFollowersButton',
        "'Add followers' button should be displayed for the writable record",
    );
    const followersList = document.querySelectorAll('.o_Follower');
    assert.containsOnce(
        followersList[0],
        '.o_Follower_editButton',
        "should display edit button for a follower related to current user",
    );
    assert.containsOnce(
        followersList[0],
        '.o_Follower_removeButton',
        "should display remove button for a follower related to current user",
    );
    assert.containsOnce(
        followersList[1],
        '.o_Follower_editButton',
        "should display edit button for other followers also on the writable record",
    );
    assert.containsOnce(
        followersList[1],
        '.o_Follower_removeButton',
        "should display remove button for other followers also on the writable record",
    );
});

QUnit.test('Show "No Followers" dropdown-item if there are no followers and user dose not have write access', async function (assert) {
    assert.expect(1);

    const { messaging, widget } = await start();
    const thread = messaging.models['Thread'].create({
        id: 100,
        model: 'res.partner',
        hasWriteAccess: false,
    });

    await this.createFollowerListMenuComponent(thread, widget.el);
    await afterNextRender(() => {
        document.querySelector('.o_FollowerListMenu_buttonFollowers').click();
    });
    assert.containsOnce(
        document.body,
        '.o_FollowerListMenu_noFollowers.disabled',
        "should display 'No Followers' dropdown-item",
    );
});

});
});
