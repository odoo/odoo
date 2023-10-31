/** @odoo-module **/

import {
    afterEach,
    afterNextRender,
    beforeEach,
    start,
} from '@mail/utils/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('channel_invitation_form', {}, function () {
QUnit.module('channel_invitation_form_tests.js', {
    beforeEach() {
        beforeEach(this);

        this.start = async params => {
            const { env, widget } = await start(Object.assign({}, params, {
                autoOpenDiscuss: true,
                data: this.data,
                hasDiscuss: true,
            }));
            this.env = env;
            this.widget = widget;
        };
    },
    afterEach() {
        afterEach(this);
    },
});

QUnit.test('should display the channel invitation form after clicking on the invite button of a chat', async function (assert) {
    assert.expect(1);

    this.data['res.partner'].records.push({
        id: 11,
        email: "testpartner@odoo.com",
        name: "TestPartner",
    });
    this.data['res.users'].records.push({
        partner_id: 11,
    });
    this.data['mail.channel'].records.push({
        channel_type: 'chat',
        id: 13,
        members: [this.data.currentPartnerId, 11],
        public: 'private',
    });
    await this.start({
        discuss: {
            context: {
                active_id: 13,
            },
        },
    });
    await afterNextRender(() => document.querySelector(`.o_ThreadViewTopbar_inviteButton`).click());
    assert.containsOnce(
        document.body,
        '.o_ChannelInvitationForm',
        "should display the channel invitation form after clicking on the invite button of a chat"
    );
});

QUnit.test('should be able to search for a new user to invite from an existing chat', async function (assert) {
    assert.expect(1);

    this.data['res.partner'].records.push({
        id: 11,
        email: "testpartner@odoo.com",
        name: "TestPartner",
    });
    this.data['res.partner'].records.push({
        id: 12,
        email: "testpartner2@odoo.com",
        name: "TestPartner2",
    });
    this.data['res.users'].records.push({
        partner_id: 11,
    });
    this.data['res.users'].records.push({
        partner_id: 12,
    });
    this.data['mail.channel'].records.push({
        channel_type: 'chat',
        id: 13,
        members: [this.data.currentPartnerId, 11],
        public: 'private',
    });
    await this.start({
        discuss: {
            context: {
                active_id: 13,
            },
        },
    });
    await afterNextRender(() => document.querySelector(`.o_ThreadViewTopbar_inviteButton`).click());
    await afterNextRender(() => document.execCommand('insertText', false, "TestPartner2"));
    assert.strictEqual(
       document.querySelector(`.o_ChannelInvitationForm_selectablePartnerName`).textContent,
       "TestPartner2",
       "should display 'TestPartner2' as it matches search term",
    );
});

QUnit.test('should be able to create a new group chat from an existing chat', async function (assert) {
    assert.expect(1);

    this.data['res.partner'].records.push({
        id: 11,
        email: "testpartner@odoo.com",
        name: "TestPartner",
    });
    this.data['res.partner'].records.push({
        id: 12,
        email: "testpartner2@odoo.com",
        name: "TestPartner2",
    });
    this.data['res.users'].records.push({
        partner_id: 11,
    });
    this.data['res.users'].records.push({
        partner_id: 12,
    });
    this.data['mail.channel'].records.push({
        channel_type: 'chat',
        id: 13,
        members: [this.data.currentPartnerId, 11],
        public: 'private',
    });
    await this.start({
        discuss: {
            context: {
                active_id: 13,
            },
        },
    });

    await afterNextRender(() => document.querySelector(`.o_ThreadViewTopbar_inviteButton`).click());
    await afterNextRender(() => document.execCommand('insertText', false, "TestPartner2"));
    document.querySelector(`.o_ChannelInvitationForm_selectablePartnerCheckbox`).click();
    await afterNextRender(() => document.querySelector(`.o_ChannelInvitationForm_inviteButton`).click());
    await afterNextRender(() => document.querySelector(`.o_ChannelInvitationForm_inviteButton`).click());
    assert.strictEqual(
       document.querySelector(`.o_ThreadViewTopbar_threadName`).textContent,
       'Mitchell Admin, TestPartner, TestPartner2',
       "should have created a new group chat with the existing chat members and the selected user",
    );
});

});
});
});
