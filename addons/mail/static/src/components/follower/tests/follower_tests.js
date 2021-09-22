/** @odoo-module **/

import { insert, link } from '@mail/model/model_field_command';
import { makeDeferred } from '@mail/utils/deferred/deferred';
import {
    afterEach,
    afterNextRender,
    beforeEach,
    createRootMessagingComponent,
    start,
} from '@mail/utils/test_utils';

import Bus from 'web.Bus';

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('follower', {}, function () {
QUnit.module('follower_tests.js', {
    beforeEach() {
        beforeEach(this);

        this.createFollowerComponent = async (follower) => {
            await createRootMessagingComponent(this, "Follower", {
                props: { followerLocalId: follower.localId },
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

QUnit.test('base rendering not editable', async function (assert) {
    assert.expect(5);

    await this.start();

    const thread = this.messaging.models['mail.thread'].create({
        id: 100,
        model: 'res.partner',
    });
    const follower = await this.messaging.models['mail.follower'].create({
        partner: insert({
            id: 1,
            name: "François Perusse",
        }),
        followedThread: link(thread),
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

    await this.start();
    const thread = this.messaging.models['mail.thread'].create({
        id: 100,
        model: 'res.partner',
    });
    const follower = await this.messaging.models['mail.follower'].create({
        partner: insert({
            id: 1,
            name: "François Perusse",
        }),
        followedThread: link(thread),
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

QUnit.test('click on partner follower details', async function (assert) {
    assert.expect(7);

    const openFormDef = makeDeferred();
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
        openFormDef.resolve();
    });
    this.data['res.partner'].records.push({ id: 100 });
    await this.start({
        env: { bus },
    });
    const thread = this.messaging.models['mail.thread'].create({
        id: 100,
        model: 'res.partner',
    });
    const follower = await this.messaging.models['mail.follower'].create({
        followedThread: link(thread),
        id: 2,
        isActive: true,
        isEditable: true,
        partner: insert({
            email: "bla@bla.bla",
            id: this.messaging.currentPartner.id,
            name: "François Perusse",
        }),
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
    await openFormDef;
    assert.verifySteps(
        ['do_action'],
        "clicking on follower should redirect to partner form view"
    );
});

QUnit.test('click on edit follower', async function (assert) {
    assert.expect(5);

    this.data['res.partner'].records.push({ id: 100, message_follower_ids: [2] });
    this.data['mail.followers'].records.push({
        id: 2,
        is_active: true,
        is_editable: true,
        partner_id: this.data.currentPartnerId,
        res_id: 100,
        res_model: 'res.partner',
    });
    await this.start({
        hasDialog: true,
        async mockRPC(route, args) {
            if (route.includes('/mail/read_subscription_data')) {
                assert.step('fetch_subtypes');
            }
            return this._super(...arguments);
        },
    });
    const thread = this.messaging.models['mail.thread'].create({
        id: 100,
        model: 'res.partner',
    });
    await thread.refreshFollowers();
    await this.createFollowerComponent(thread.followers[0]);
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

QUnit.test('edit follower and close subtype dialog', async function (assert) {
    assert.expect(6);

    this.data['res.partner'].records.push({ id: 100 });
    await this.start({
        hasDialog: true,
        async mockRPC(route, args) {
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
    const thread = this.messaging.models['mail.thread'].create({
        id: 100,
        model: 'res.partner',
    });
    const follower = await this.messaging.models['mail.follower'].create({
        followedThread: link(thread),
        id: 2,
        isActive: true,
        isEditable: true,
        partner: insert({
            email: "bla@bla.bla",
            id: this.messaging.currentPartner.id,
            name: "François Perusse",
        }),
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
        "dialog allowing to edit follower subtypes should have been created"
    );

    await afterNextRender(
        () => document.querySelector('.o_FollowerSubtypeList_closeButton').click()
    );
    assert.containsNone(
        document.body,
        '.o_DialogManager_dialog',
        "follower subtype dialog should be closed after clicking on close button"
    );
});

});
});
});
