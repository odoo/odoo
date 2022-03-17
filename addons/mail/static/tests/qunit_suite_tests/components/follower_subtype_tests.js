/** @odoo-module **/

import { insert, link } from '@mail/model/model_field_command';
import {
    afterNextRender,
    beforeEach,
    createRootMessagingComponent,
    start,
} from '@mail/utils/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('follower_subtype_tests.js', {
    async beforeEach() {
        await beforeEach(this);

        this.createFollowerSubtypeComponent = async ({ follower, followerSubtype, target }) => {
            const props = {
                followerLocalId: follower.localId,
                followerSubtypeLocalId: followerSubtype.localId,
            };
            await createRootMessagingComponent(follower.env, "FollowerSubtype", {
                props,
                target,
            });
        };
    },
});

QUnit.test('simplest layout of a followed subtype', async function (assert) {
    assert.expect(5);

    const { messaging, widget } = await start({ data: this.data });

    const thread = messaging.models['Thread'].create({
        id: 100,
        model: 'res.partner',
    });
    const follower = messaging.models['Follower'].create({
        partner: insert({
            id: 1,
            name: "François Perusse",
        }),
        followedThread: link(thread),
        id: 2,
        isActive: true,
        isEditable: true,
    });
    const followerSubtype = messaging.models['FollowerSubtype'].create({
        id: 1,
        isDefault: true,
        isInternal: false,
        name: "Dummy test",
        resModel: 'res.partner'
    });
    follower.update({
        selectedSubtypes: link(followerSubtype),
        subtypes: link(followerSubtype),
    });
    await this.createFollowerSubtypeComponent({
        follower,
        followerSubtype,
        target: widget.el,
    });
    assert.containsOnce(
        document.body,
        '.o_FollowerSubtype',
        "should have follower subtype component"
    );
    assert.containsOnce(
        document.body,
        '.o_FollowerSubtype_label',
        "should have a label"
    );
    assert.containsOnce(
        document.body,
        '.o_FollowerSubtype_checkbox',
        "should have a checkbox"
    );
    assert.strictEqual(
        document.querySelector('.o_FollowerSubtype_label').textContent,
        "Dummy test",
        "should have the name of the subtype as label"
    );
    assert.ok(
        document.querySelector('.o_FollowerSubtype_checkbox').checked,
        "checkbox should be checked as follower subtype is followed"
    );
});

QUnit.test('simplest layout of a not followed subtype', async function (assert) {
    assert.expect(5);

    const { messaging, widget } = await start({ data: this.data });

    const thread = messaging.models['Thread'].create({
        id: 100,
        model: 'res.partner',
    });
    const follower = messaging.models['Follower'].create({
        partner: insert({
            id: 1,
            name: "François Perusse",
        }),
        followedThread: link(thread),
        id: 2,
        isActive: true,
        isEditable: true,
    });
    const followerSubtype = messaging.models['FollowerSubtype'].create({
        id: 1,
        isDefault: true,
        isInternal: false,
        name: "Dummy test",
        resModel: 'res.partner'
    });
    follower.update({ subtypes: link(followerSubtype) });
    await this.createFollowerSubtypeComponent({
        follower,
        followerSubtype,
        target: widget.el,
    });
    assert.containsOnce(
        document.body,
        '.o_FollowerSubtype',
        "should have follower subtype component"
    );
    assert.containsOnce(
        document.body,
        '.o_FollowerSubtype_label',
        "should have a label"
    );
    assert.containsOnce(
        document.body,
        '.o_FollowerSubtype_checkbox',
        "should have a checkbox"
    );
    assert.strictEqual(
        document.querySelector('.o_FollowerSubtype_label').textContent,
        "Dummy test",
        "should have the name of the subtype as label"
    );
    assert.notOk(
        document.querySelector('.o_FollowerSubtype_checkbox').checked,
        "checkbox should not be checked as follower subtype is not followed"
    );
});

QUnit.test('toggle follower subtype checkbox', async function (assert) {
    assert.expect(5);

    const { messaging, widget } = await start({ data: this.data });

    const thread = messaging.models['Thread'].create({
        id: 100,
        model: 'res.partner',
    });
    const follower = messaging.models['Follower'].create({
        partner: insert({
            id: 1,
            name: "François Perusse",
        }),
        followedThread: link(thread),
        id: 2,
        isActive: true,
        isEditable: true,
    });
    const followerSubtype = messaging.models['FollowerSubtype'].create({
        id: 1,
        isDefault: true,
        isInternal: false,
        name: "Dummy test",
        resModel: 'res.partner'
    });
    follower.update({ subtypes: link(followerSubtype) });
    await this.createFollowerSubtypeComponent({
        follower,
        followerSubtype,
        target: widget.el,
    });
    assert.containsOnce(
        document.body,
        '.o_FollowerSubtype',
        "should have follower subtype component"
    );
    assert.containsOnce(
        document.body,
        '.o_FollowerSubtype_checkbox',
        "should have a checkbox"
    );
    assert.notOk(
        document.querySelector('.o_FollowerSubtype_checkbox').checked,
        "checkbox should not be checked as follower subtype is not followed"
    );

    await afterNextRender(() =>
        document.querySelector('.o_FollowerSubtype_checkbox').click()
    );
    assert.ok(
        document.querySelector('.o_FollowerSubtype_checkbox').checked,
        "checkbox should now be checked"
    );

    await afterNextRender(() =>
        document.querySelector('.o_FollowerSubtype_checkbox').click()
    );
    assert.notOk(
        document.querySelector('.o_FollowerSubtype_checkbox').checked,
        "checkbox should be no more checked"
    );
});

});
});
