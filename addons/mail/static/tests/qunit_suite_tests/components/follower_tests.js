/** @odoo-module **/

import { insert, replace } from '@mail/model/model_field_command';
import { makeDeferred } from '@mail/utils/deferred';
import {
    createRootMessagingComponent,
    start,
    startServer,
} from '@mail/../tests/helpers/test_utils';

import Bus from 'web.Bus';

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('follower_tests.js', {
    beforeEach() {
        this.createFollowerComponent = async (follower, target) => {
            await createRootMessagingComponent(follower.env, "Follower", {
                props: { follower },
                target,
            });
        };
    },
});

QUnit.test('base rendering not editable', async function (assert) {
    assert.expect(5);

    const { messaging, target } = await start();

    const thread = messaging.models['Thread'].create({
        hasWriteAccess: false,
        id: 100,
        model: 'res.partner',
    });
    const follower = await messaging.models['Follower'].create({
        partner: insert({
            id: 1,
            name: "François Perusse",
        }),
        followedThread: replace(thread),
        id: 2,
        isActive: true,
    });
    await this.createFollowerComponent(follower, target);
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

    const { messaging, target } = await start();
    const thread = messaging.models['Thread'].create({
        hasWriteAccess: true,
        id: 100,
        model: 'res.partner',
    });
    const follower = await messaging.models['Follower'].create({
        partner: insert({
            id: 1,
            name: "François Perusse",
        }),
        followedThread: replace(thread),
        id: 2,
        isActive: true,
    });
    await this.createFollowerComponent(follower, target);
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
    bus.on('do-action', null, ({ action }) => {
            assert.step('do_action');
            assert.strictEqual(
                action.res_id,
                3,
                "The redirect action should redirect to the right res id (3)"
            );
            assert.strictEqual(
                action.res_model,
                'res.partner',
                "The redirect action should redirect to the right res model (res.partner)"
            );
            assert.strictEqual(
                action.type,
                "ir.actions.act_window",
                "The redirect action should be of type 'ir.actions.act_window'"
            );
            openFormDef.resolve();
    });
    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create();
    const { messaging, target } = await start({ env: { bus } });
    const thread = messaging.models['Thread'].create({
        id: resPartnerId1,
        model: 'res.partner',
    });
    const follower = await messaging.models['Follower'].create({
        followedThread: replace(thread),
        id: 2,
        isActive: true,
        partner: insert({
            email: "bla@bla.bla",
            id: messaging.currentPartner.id,
            name: "François Perusse",
        }),
    });
    await this.createFollowerComponent(follower, target);
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

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create();
    pyEnv['mail.followers'].create({
        is_active: true,
        partner_id: pyEnv.currentPartnerId,
        res_id: resPartnerId1,
        res_model: 'res.partner',
    });
    const { click, messaging, target } = await start({
        async mockRPC(route, args) {
            if (route.includes('/mail/read_subscription_data')) {
                assert.step('fetch_subtypes');
            }
            return this._super(...arguments);
        },
    });
    const thread = messaging.models['Thread'].create({
        id: resPartnerId1,
        model: 'res.partner',
    });
    await thread.fetchData(['followers']);
    await this.createFollowerComponent(thread.followers[0], target);
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

    await click('.o_Follower_editButton');
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

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create();
    const { click, messaging, target } = await start({
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
    const thread = messaging.models['Thread'].create({
        id: resPartnerId1,
        model: 'res.partner',
    });
    const follower = await messaging.models['Follower'].create({
        followedThread: replace(thread),
        id: 2,
        isActive: true,
        partner: insert({
            email: "bla@bla.bla",
            id: messaging.currentPartner.id,
            name: "François Perusse",
        }),
    });
    await this.createFollowerComponent(follower, target);
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

    await click('.o_Follower_editButton');
    assert.verifySteps(
        ['fetch_subtypes'],
        "clicking on edit follower should fetch subtypes"
    );
    assert.containsOnce(
        document.body,
        '.o_FollowerSubtypeList',
        "dialog allowing to edit follower subtypes should have been created"
    );

    await click('.o_FollowerSubtypeList_closeButton');
    assert.containsNone(
        document.body,
        '.o_DialogManager_dialog',
        "follower subtype dialog should be closed after clicking on close button"
    );
});

});
});
