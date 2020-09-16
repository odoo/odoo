odoo.define('mail/static/src/components/follower_subtype/follower_subtype_tests.js', function (require) {
'use strict';

const components = {
    FollowerSubtype: require('mail/static/src/components/follower_subtype/follower_subtype.js'),
};
const {
    afterEach,
    afterNextRender,
    beforeEach,
    createRootComponent,
    start,
} = require('mail/static/src/utils/test_utils.js');

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('follower_subtype', {}, function () {
QUnit.module('follower_subtype_tests.js', {
    beforeEach() {
        beforeEach(this);

        this.createFollowerSubtypeComponent = async ({ follower, followerSubtype }) => {
            const props = {
                followerLocalId: follower.localId,
                followerSubtypeLocalId: followerSubtype.localId,
            };
            await createRootComponent(this, components.FollowerSubtype, {
                props,
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

QUnit.test('simplest layout of a followed subtype', async function (assert) {
    assert.expect(5);

    await this.start();

    const thread = this.env.models['mail.thread'].create({
        __mfield_id: 100,
        __mfield_model: 'res.partner',
    });
    const follower = this.env.models['mail.follower'].create({
        __mfield_channel: [['insert', {
            __mfield_id: 1,
            __mfield_model: 'mail.channel',
            __mfield_name: "François Perusse",
        }]],
        __mfield_followedThread: [['link', thread]],
        __mfield_id: 2,
        __mfield_isActive: true,
        __mfield_isEditable: true,
    });
    const followerSubtype = this.env.models['mail.follower_subtype'].create({
        __mfield_id: 1,
        __mfield_isDefault: true,
        __mfield_isInternal: false,
        __mfield_name: "Dummy test",
        __mfield_resModel: 'res.partner'
    });
    follower.update({
        __mfield_selectedSubtypes: [['link', followerSubtype]],
        __mfield_subtypes: [['link', followerSubtype]],
    });
    await this.createFollowerSubtypeComponent({
        follower,
        followerSubtype,
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

    await this.start();

    const thread = this.env.models['mail.thread'].create({
        __mfield_id: 100,
        __mfield_model: 'res.partner',
    });
    const follower = this.env.models['mail.follower'].create({
        __mfield_channel: [['insert', {
            __mfield_id: 1,
            __mfield_model: 'mail.channel',
            __mfield_name: "François Perusse",
        }]],
        __mfield_followedThread: [['link', thread]],
        __mfield_id: 2,
        __mfield_isActive: true,
        __mfield_isEditable: true,
    });
    const followerSubtype = this.env.models['mail.follower_subtype'].create({
        __mfield_id: 1,
        __mfield_isDefault: true,
        __mfield_isInternal: false,
        __mfield_name: "Dummy test",
        __mfield_resModel: 'res.partner'
    });
    follower.update({ __mfield_subtypes: [['link', followerSubtype]] });
    await this.createFollowerSubtypeComponent({
        follower,
        followerSubtype,
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

    await this.start();

    const thread = this.env.models['mail.thread'].create({
        __mfield_id: 100,
        __mfield_model: 'res.partner',
    });
    const follower = this.env.models['mail.follower'].create({
        __mfield_channel: [['insert', {
            __mfield_id: 1,
            __mfield_model: 'mail.channel',
            __mfield_name: "François Perusse",
        }]],
        __mfield_followedThread: [['link', thread]],
        __mfield_id: 2,
        __mfield_isActive: true,
        __mfield_isEditable: true,
    });
    const followerSubtype = this.env.models['mail.follower_subtype'].create({
        __mfield_id: 1,
        __mfield_isDefault: true,
        __mfield_isInternal: false,
        __mfield_name: "Dummy test",
        __mfield_resModel: 'res.partner'
    });
    follower.update({ __mfield_subtypes: [['link', followerSubtype]] });
    await this.createFollowerSubtypeComponent({
        follower,
        followerSubtype,
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
});

});
