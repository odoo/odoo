odoo.define('mail/static/src/components/follow_button/follow_button_tests.js', function (require) {
'use strict';

const components = {
    FollowButton: require('mail/static/src/components/follow_button/follow_button.js'),
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
QUnit.module('follow_button', {}, function () {
QUnit.module('follow_button_tests.js', {
    beforeEach() {
        beforeEach(this);

        this.createFollowButtonComponent = async (thread, otherProps = {}) => {
            const props = Object.assign({ threadLocalId: thread.localId }, otherProps);
            await createRootComponent(this, components.FollowButton, {
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

QUnit.test('base rendering not editable', async function (assert) {
    assert.expect(3);

    await this.start();
    const thread = this.env.models['mail.thread'].create({
        id: 100,
        model: 'res.partner',
    });
    await this.createFollowButtonComponent(thread, { isDisabled: true });
    assert.containsOnce(
        document.body,
        '.o_FollowButton',
        "should have follow button component"
    );
    assert.containsOnce(
        document.body,
        '.o_FollowButton_follow',
        "should have 'Follow' button"
    );
    assert.ok(
        document.querySelector('.o_FollowButton_follow').disabled,
        "'Follow' button should be disabled"
    );
});

QUnit.test('base rendering editable', async function (assert) {
    assert.expect(3);

    await this.start();
    const thread = this.env.models['mail.thread'].create({
        id: 100,
        model: 'res.partner',
    });
    await this.createFollowButtonComponent(thread);
    assert.containsOnce(
        document.body,
        '.o_FollowButton',
        "should have follow button component"
    );
    assert.containsOnce(
        document.body,
        '.o_FollowButton_follow',
        "should have 'Follow' button"
    );
    assert.notOk(
        document.querySelector('.o_FollowButton_follow').disabled,
        "'Follow' button should be disabled"
    );
});

QUnit.test('hover following button', async function (assert) {
    assert.expect(8);

    this.data['res.partner'].records.push({ id: 100, message_follower_ids: [1] });
    this.data['mail.followers'].records.push({
        id: 1,
        is_active: true,
        is_editable: true,
        partner_id: this.data.currentPartnerId,
        res_id: 100,
        res_model: 'res.partner',
    });
    await this.start();
    const thread = this.env.models['mail.thread'].create({
        id: 100,
        model: 'res.partner',
    });
    thread.follow();
    await this.createFollowButtonComponent(thread);
    assert.containsOnce(
        document.body,
        '.o_FollowButton',
        "should have follow button component"
    );
    assert.containsOnce(
        document.body,
        '.o_FollowButton_unfollow',
        "should have 'Unfollow' button"
    );
    assert.strictEqual(
        document.querySelector('.o_FollowButton_unfollow').textContent.trim(),
        'Following',
        "'unfollow' button should display 'Following' as text when not hovered"
    );
    assert.containsNone(
        document.querySelector('.o_FollowButton_unfollow'),
        '.fa-times',
        "'unfollow' button should not contain a cross icon when not hovered"
    );
    assert.containsOnce(
        document.querySelector('.o_FollowButton_unfollow'),
        '.fa-check',
        "'unfollow' button should contain a check icon when not hovered"
    );

    await afterNextRender(() => {
        document
            .querySelector('.o_FollowButton_unfollow')
            .dispatchEvent(new window.MouseEvent('mouseenter'));
        }
    );
    assert.strictEqual(
        document.querySelector('.o_FollowButton_unfollow').textContent.trim(),
        'Unfollow',
        "'unfollow' button should display 'Unfollow' as text when hovered"
    );
    assert.containsOnce(
        document.querySelector('.o_FollowButton_unfollow'),
        '.fa-times',
        "'unfollow' button should contain a cross icon when hovered"
    );
    assert.containsNone(
        document.querySelector('.o_FollowButton_unfollow'),
        '.fa-check',
        "'unfollow' button should not contain a check icon when hovered"
    );
});

QUnit.test('click on "follow" button', async function (assert) {
    assert.expect(7);

    this.data['res.partner'].records.push({ id: 100, message_follower_ids: [1] });
    this.data['mail.followers'].records.push({
        id: 1,
        is_active: true,
        is_editable: true,
        partner_id: this.data.currentPartnerId,
        res_id: 100,
        res_model: 'res.partner',
    });
    await this.start({
        async mockRPC(route, args) {
            if (route.includes('message_subscribe')) {
                assert.step('rpc:message_subscribe');
            } else if (route.includes('mail/read_followers')) {
                assert.step('rpc:mail/read_followers');
            }
            return this._super(...arguments);
        },
    });
    const thread = this.env.models['mail.thread'].create({
        id: 100,
        model: 'res.partner',
    });
    await this.createFollowButtonComponent(thread);
    assert.containsOnce(
        document.body,
        '.o_FollowButton',
        "should have follow button component"
    );
    assert.containsOnce(
        document.body,
        '.o_FollowButton_follow',
        "should have button follow"
    );

    await afterNextRender(() => {
        document.querySelector('.o_FollowButton_follow').click();
    });
    assert.verifySteps([
        'rpc:message_subscribe',
        'rpc:mail/read_followers',
    ]);
    assert.containsNone(
        document.body,
        '.o_FollowButton_follow',
        "should not have follow button after clicked on follow"
    );
    assert.containsOnce(
        document.body,
        '.o_FollowButton_unfollow',
        "should have unfollow button after clicked on follow"
    );
});

QUnit.test('click on "unfollow" button', async function (assert) {
    assert.expect(7);

    this.data['res.partner'].records.push({ id: 100, message_follower_ids: [1] });
    this.data['mail.followers'].records.push({
        id: 1,
        is_active: true,
        is_editable: true,
        partner_id: this.data.currentPartnerId,
        res_id: 100,
        res_model: 'res.partner',
    });
    await this.start({
        async mockRPC(route, args) {
            if (route.includes('message_unsubscribe')) {
                assert.step('rpc:message_unsubscribe');
            }
            return this._super(...arguments);
        },
    });
    const thread = this.env.models['mail.thread'].create({
        id: 100,
        model: 'res.partner',
    });
    thread.follow();
    await this.createFollowButtonComponent(thread);
    assert.containsOnce(
        document.body,
        '.o_FollowButton',
        "should have follow button component"
    );
    assert.containsNone(
        document.body,
        '.o_FollowButton_follow',
        "should not have button follow"
    );
    assert.containsOnce(
        document.body,
        '.o_FollowButton_unfollow',
        "should have button unfollow"
    );

    await afterNextRender(() => document.querySelector('.o_FollowButton_unfollow').click());
    assert.verifySteps(['rpc:message_unsubscribe']);
    assert.containsOnce(
        document.body,
        '.o_FollowButton_follow',
        "should have follow button after clicked on unfollow"
    );
    assert.containsNone(
        document.body,
        '.o_FollowButton_unfollow',
        "should not have unfollow button after clicked on unfollow"
    );
});

});
});
});

});
