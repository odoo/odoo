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
        id: 100,
        model: 'res.partner',
    });
    const follower = this.env.models['mail.follower'].create({
        channel: [['insert', {
            id: 1,
            model: 'mail.channel',
            name: "François Perusse",
        }]],
        followedThread: [['link', thread]],
        id: 2,
        isActive: true,
        isEditable: true,
    });
    const followerSubtype = this.env.models['mail.follower_subtype'].create({
        id: 1,
        isDefault: true,
        isInternal: false,
        name: "Dummy test",
        resModel: 'res.partner'
    });
    follower.update({
        selectedSubtypes: [['link', followerSubtype]],
        subtypes: [['link', followerSubtype]],
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
        id: 100,
        model: 'res.partner',
    });
    const follower = this.env.models['mail.follower'].create({
        channel: [['insert', {
            id: 1,
            model: 'mail.channel',
            name: "François Perusse",
        }]],
        followedThread: [['link', thread]],
        id: 2,
        isActive: true,
        isEditable: true,
    });
    const followerSubtype = this.env.models['mail.follower_subtype'].create({
        id: 1,
        isDefault: true,
        isInternal: false,
        name: "Dummy test",
        resModel: 'res.partner'
    });
    follower.update({ subtypes: [['link', followerSubtype]] });
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
        id: 100,
        model: 'res.partner',
    });
    const follower = this.env.models['mail.follower'].create({
        channel: [['insert', {
            id: 1,
            model: 'mail.channel',
            name: "François Perusse",
        }]],
        followedThread: [['link', thread]],
        id: 2,
        isActive: true,
        isEditable: true,
    });
    const followerSubtype = this.env.models['mail.follower_subtype'].create({
        id: 1,
        isDefault: true,
        isInternal: false,
        name: "Dummy test",
        resModel: 'res.partner'
    });
    follower.update({ subtypes: [['link', followerSubtype]] });
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
