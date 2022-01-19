/** @odoo-module **/

import { insert, insertAndReplace, link, replace } from '@mail/model/model_field_command';
import { makeDeferred } from '@mail/utils/deferred/deferred';
import { afterEach, afterNextRender, beforeEach, start } from '@mail/utils/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('message_reaction_group', {}, function () {
QUnit.module('message_reaction_group_tests.js', {
    async beforeEach() {
        await beforeEach(this);

        this.start = async params => {
            const res = await start({ ...params,
                data: this.data,
                hasDiscuss: true,
            });
            const { apps, env, widget } = res;
            this.apps = apps;
            this.env = env;
            this.widget = widget;
            return res;
        };
    },
    afterEach() {
        afterEach(this);
    },
});

QUnit.test('UI should reflect single reaction linked to message', async function (assert) {
    assert.expect(3);

    this.data['mail.channel'].records.push({
        channel_type: 'channel',
        id: 20,
        members: [this.data.currentPartnerId],
        name: 'test channel',
        public: 'public',
    });
    this.data['mail.message'].records.push({
        body: 'not empty',
        id: 10,
        message_type: 'comment',
        model: 'mail.channel',
        res_id: 20,
    });
    this.data['mail.message.reaction'].records.push({
        content: '😊',
        message_id: 10,
        partner_id: 7,
    });
    const { click, openDiscuss } = await this.start({
        discuss: {
            params: {
                default_active_id: 'mail.channel_20',
            },
        },
    });
    await openDiscuss();
    assert.containsOnce(
        document.body,
        '.o_MessageReactionGroup',
        "should have one reaction"
    );
    assert.strictEqual(
        document.querySelector('.o_MessageReactionGroup_content').textContent,
        "😊",
        "should have 😊 reaction",
    );
    assert.strictEqual(
        document.querySelector('.o_MessageReactionGroup_count').textContent,
        "1",
        "😊 reaction should have only 1 partner having reacted",
    );
});

QUnit.test('increase the number of reacting users for a same reaction', async function (assert) {
    assert.expect(1);

    this.data['mail.channel'].records.push({
        channel_type: 'channel',
        id: 20,
        members: [this.data.currentPartnerId],
        name: 'test channel',
        public: 'public',
    });
    this.data['mail.message'].records.push({
        body: 'not empty',
        id: 10,
        message_type: 'comment',
        model: 'mail.channel',
        res_id: 20,
    });
    this.data['mail.message.reaction'].records.push({
        content: '😊',
        message_id: 10,
        partner_id: 7,
    });
    const { click, openDiscuss } = await this.start({
        discuss: {
            params: {
                default_active_id: 'mail.channel_20',
            },
        },
    });
    await openDiscuss();
    await afterNextRender(() =>
        document.querySelector('.o_MessageReactionGroup').click()
    );
    assert.strictEqual(
        document.querySelector('.o_MessageReactionGroup_count').textContent,
        "2",
        "😊 reaction should have 2 partners having reacted",
    );
});

QUnit.test('decrease the number of reacting users for a same reaction', async function (assert) {
    assert.expect(1);

    this.data['mail.channel'].records.push({
        channel_type: 'channel',
        id: 20,
        members: [this.data.currentPartnerId],
        name: 'test channel',
        public: 'public',
    });
    this.data['mail.message'].records.push({
        body: 'not empty',
        id: 10,
        message_type: 'comment',
        model: 'mail.channel',
        res_id: 20,
    });
    this.data['mail.message.reaction'].records.push({
        content: '😊',
        message_id: 10,
        partner_id: 7,
    });
    const { click, openDiscuss } = await this.start({
        discuss: {
            params: {
                default_active_id: 'mail.channel_20',
            },
        },
    });
    await openDiscuss();
    await afterNextRender(() =>
        document.querySelector('.o_MessageReactionGroup').click()
    );
    await afterNextRender(() =>
        document.querySelector('.o_MessageReactionGroup').click()
    );
    assert.strictEqual(
        document.querySelector('.o_MessageReactionGroup_count').textContent,
        "1",
        "😊 reaction should have 1 partner having reacted",
    );
});

QUnit.test('add an other reaction to a message', async function (assert) {
    assert.expect(1);

    this.data['mail.channel'].records.push({
        channel_type: 'channel',
        id: 20,
        members: [this.data.currentPartnerId],
        name: 'test channel',
        public: 'public',
    });
    this.data['mail.message'].records.push({
        body: 'not empty',
        id: 10,
        message_type: 'comment',
        model: 'mail.channel',
        res_id: 20,
    });
    this.data['mail.message.reaction'].records.push({
        content: '😊',
        message_id: 10,
        partner_id: 7,
    });
    const { click, openDiscuss } = await this.start({
        discuss: {
            params: {
                default_active_id: 'mail.channel_20',
            },
        },
    });
    await openDiscuss();
    await afterNextRender(() =>
        document.querySelector('.o_Message').click()
    );
    await afterNextRender(() =>
        document.querySelector('.o_MessageActionList_actionReaction').click()
    );
    await afterNextRender(() =>
        document.querySelector('.o_EmojiList_emoji[data-unicode=\'😃\']').click()
    );
    assert.containsN(
        document.body,
        '.o_MessageReactionGroup',
        2,
        "should have 2 reactions"
    );
});

QUnit.test('when current user clicks on a lone-and-self reaction, it should remove the reaction group', async function (assert) {
    assert.expect(1);

    this.data['mail.channel'].records.push({
        channel_type: 'channel',
        id: 20,
        members: [this.data.currentPartnerId],
        name: 'test channel',
        public: 'public',
    });
    this.data['mail.message'].records.push({
        body: 'not empty',
        id: 10,
        message_type: 'comment',
        model: 'mail.channel',
        res_id: 20,
    });
    this.data['mail.message.reaction'].records.push({
        content: '😊',
        message_id: 10,
        partner_id: 3,
    });
    const { click, openDiscuss } = await this.start({
        discuss: {
            params: {
                default_active_id: 'mail.channel_20',
            },
        },
    });
    await openDiscuss();
    await afterNextRender(() =>
        document.querySelector('.o_MessageReactionGroup').click()
    );
    assert.containsNone(
        document.body,
        '.o_MessageReactionGroup',
        "should have no reaction left"
    );
});

QUnit.test('UI should reflect single guest reaction linked to message', async function (assert) {
    assert.expect(3);

    this.data['mail.guest'].records.push({ id: 30, name: "Demo Guest" });
    this.data['mail.channel'].records.push({
        channel_type: 'channel',
        id: 20,
        members: [this.data.currentPartnerId],
        name: 'test channel',
        public: 'public',
    });
    this.data['mail.message'].records.push({
        body: 'not empty',
        id: 10,
        message_type: 'comment',
        model: 'mail.channel',
        res_id: 20,
    });
    this.data['mail.message.reaction'].records.push({
        content: '😊',
        message_id: 10,
        guest_id: 30,
    });
    const { click, openDiscuss } = await this.start({
        discuss: {
            params: {
                default_active_id: 'mail.channel_20',
            },
        },
    });
    await openDiscuss();
    assert.containsOnce(
        document.body,
        '.o_MessageReactionGroup',
        "should have one reaction"
    );
    assert.strictEqual(
        document.querySelector('.o_MessageReactionGroup_content').textContent,
        "😊",
        "should have 😊 reaction",
    );
    assert.strictEqual(
        document.querySelector('.o_MessageReactionGroup_count').textContent,
        "1",
        "😊 reaction should have only 1 partner having reacted",
    );
});

QUnit.only('Add a message reaction group to a message as a guest user', async function (assert) {
    assert.expect(1);

    this.data.currentGuestId = 5;
    this.data['mail.guest'].records.push({
        display_name: "Guest User",
        id: this.data.currentGuestId,
        name: "Guest User",
    });
    this.data.currentUserId = this.data.publicUserId;
    this.data['res.users'].records.push({
        display_name: "Guest User",
        id: this.data.currentUserId,
        name: "Guest User",
        partner_id: this.data.currentGuestId,
    });
    this.data['mail.channel'].records.push({
        channel_type: 'channel',
        id: 20,
        members: [this.data.currentPartnerId],
        name: 'test channel',
        public: 'public',
    });
    this.data['mail.message'].records.push({
        body: 'not empty',
        id: 10,
        message_type: 'comment',
        model: 'mail.channel',
        res_id: 20,
    });
    this.data['mail.message.reaction'].records.push({
        content: '😊',
        message_id: 10,
        partner_id: 7,
    });

    const { click, openDiscuss } = await this.start({
        discuss: {
            params: {
                default_active_id: 'mail.channel_20',
            },
        },
    });
    await openDiscuss();
    await afterNextRender(() =>
        document.querySelector('.o_MessageReactionGroup').click()
    );
    assert.strictEqual(
        document.querySelector('.o_MessageReactionGroup_count').textContent,
        "2",
        "😊 reaction should have 2 partners having reacted including a guest",
    );
    await new Promise(()=>{});
});

});
});
});
