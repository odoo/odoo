/** @odoo-module **/

import {
    afterEach,
    afterNextRender,
    beforeEach,
    start,
} from '@mail/utils/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('discuss', {}, function () {
QUnit.module('discuss_domain_tests.js', {
    beforeEach() {
        beforeEach(this);

        this.start = async params => {
            const { afterEvent, env, widget } = await start(Object.assign({}, params, {
                autoOpenDiscuss: true,
                data: this.data,
                hasDiscuss: true,
            }));
            this.afterEvent = afterEvent;
            this.env = env;
            this.widget = widget;
        };
    },
    afterEach() {
        afterEach(this);
    },
});

QUnit.test('discuss should filter messages based on given domain', async function (assert) {
    assert.expect(2);

    this.data['mail.message'].records.push({
        body: "test",
        needaction: true,
        needaction_partner_ids: [this.data.currentPartnerId],
    }, {
        body: "not empty",
        needaction: true,
        needaction_partner_ids: [this.data.currentPartnerId],
    });
    await this.start();
    assert.containsN(
        document.body,
        '.o_Message',
        2,
        "should have 2 messages in Inbox initially"
    );

    await this.afterEvent({
        eventName: 'o-thread-view-hint-processed',
        func: () => {
            // simulate control panel search
            this.env.messaging.discuss.update({
                stringifiedDomain: JSON.stringify([['body', 'ilike', 'test']]),
            });
        },
        message: "should wait until search filter is applied",
        predicate: ({ hint, threadViewer }) => {
            return (
                hint.type === 'messages-loaded' &&
                hint.data.fetchedMessages.length === 1 &&
                threadViewer.thread.model === 'mail.box' &&
                threadViewer.thread.id === 'inbox'
            );
        },
    });
    assert.containsOnce(
        document.body,
        '.o_Message',
        "should only have the 1 message containing 'test' remaining after doing a search"
    );
});

QUnit.test('discuss should keep filter domain on changing thread', async function (assert) {
    assert.expect(3);

    this.data['mail.channel'].records.push({ id: 20 });
    this.data['mail.message'].records.push({
        body: "test",
        model: "mail.channel",
        res_id: 20,
    }, {
        body: "not empty",
        model: "mail.channel",
        res_id: 20,
    });
    await this.start();
    const channel = this.env.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel',
    });
    assert.containsNone(
        document.body,
        '.o_Message',
        "should have no message in Inbox initially"
    );

    await this.afterEvent({
        eventName: 'o-thread-view-hint-processed',
        func: () => {
            // simulate control panel search
            this.env.messaging.discuss.update({
                stringifiedDomain: JSON.stringify([['body', 'ilike', 'test']]),
            });
        },
        message: "should wait until search filter is applied",
        predicate: ({ hint, threadViewer }) => {
            return (
                hint.type === 'messages-loaded' &&
                threadViewer.thread.model === 'mail.box' &&
                threadViewer.thread.id === 'inbox'
            );
        },
    });
    assert.containsNone(
        document.body,
        '.o_Message',
        "should have still no message in Inbox after doing a search"
    );

    await this.afterEvent({
        eventName: 'o-thread-view-hint-processed',
        func: () => {
            document.querySelector(`
                .o_DiscussSidebar_item[data-thread-local-id="${channel.localId}"]
            `).click();
        },
        message: "should wait until channel 20 is loaded after clicking on it",
        predicate: ({ hint, threadViewer }) => {
            return (
                hint.type === 'messages-loaded' &&
                threadViewer.thread.model === 'mail.channel' &&
                threadViewer.thread.id === 20
            );
        },
    });
    assert.containsOnce(
        document.body,
        '.o_Message',
        "should only have the 1 message containing 'test' in channel 20 (due to the domain still applied on changing thread)"
    );
});

QUnit.test('discuss should refresh filtered thread on receiving new message', async function (assert) {
    assert.expect(2);

    this.data['mail.channel'].records.push({ id: 20 });
    await this.start();
    const channel = this.env.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel',
    });
    await this.afterEvent({
        eventName: 'o-thread-view-hint-processed',
        func: () => {
            document.querySelector(`
                .o_DiscussSidebar_item[data-thread-local-id="${channel.localId}"]
            `).click();
        },
        message: "should wait until channel 20 is loaded after clicking on it",
        predicate: ({ hint, threadViewer }) => {
            return (
                hint.type === 'messages-loaded' &&
                threadViewer.thread.model === 'mail.channel' &&
                threadViewer.thread.id === 20
            );
        },
    });
    await this.afterEvent({
        eventName: 'o-thread-view-hint-processed',
        func: () => {
            // simulate control panel search
            this.env.messaging.discuss.update({
                stringifiedDomain: JSON.stringify([['body', 'ilike', 'test']]),
            });
        },
        message: "should wait until search filter is applied",
        predicate: ({ hint, threadViewer }) => {
            return (
                hint.type === 'messages-loaded' &&
                threadViewer.thread.model === 'mail.channel' &&
                threadViewer.thread.id === 20
            );
        },
    });
    assert.containsNone(
        document.body,
        '.o_Message',
        "should have initially no message in channel 20 matching the search 'test'"
    );

    // simulate receiving a message
    await this.afterEvent({
        eventName: 'o-thread-view-hint-processed',
        func: () => this.env.services.rpc({
            route: '/mail/chat_post',
            params: {
                message_content: "test",
                uuid: channel.uuid,
            },
        }),
        message: "should wait until channel 20 refreshed its filtered message list",
        predicate: data => {
            return (
                data.threadViewer.thread.model === 'mail.channel' &&
                data.threadViewer.thread.id === 20 &&
                data.hint.type === 'messages-loaded'
            );
        },
    });
    assert.containsOnce(
        document.body,
        '.o_Message',
        "should only have the 1 message containing 'test' in channel 20 after just receiving it"
    );
});

QUnit.test('discuss should refresh filtered thread on changing thread', async function (assert) {
    assert.expect(4);

    this.data['mail.channel'].records.push({ id: 20 }, { id: 21 });
    await this.start();
    const channel20 = this.env.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel',
    });
    const channel21 = this.env.models['mail.thread'].findFromIdentifyingData({
        id: 21,
        model: 'mail.channel',
    });
    await this.afterEvent({
        eventName: 'o-thread-view-hint-processed',
        func: () => {
            document.querySelector(`
                .o_DiscussSidebar_item[data-thread-local-id="${channel20.localId}"]
            `).click();
        },
        message: "should wait until channel 20 is loaded after clicking on it",
        predicate: ({ hint, threadViewer }) => {
            return (
                hint.type === 'messages-loaded' &&
                threadViewer.thread.model === 'mail.channel' &&
                threadViewer.thread.id === 20
            );
        },
    });
    await this.afterEvent({
        eventName: 'o-thread-view-hint-processed',
        func: () => {
            // simulate control panel search
            this.env.messaging.discuss.update({
                stringifiedDomain: JSON.stringify([['body', 'ilike', 'test']]),
            });
        },
        message: "should wait until search filter is applied",
        predicate: ({ hint, threadViewer }) => {
            return (
                hint.type === 'messages-loaded' &&
                threadViewer.thread.model === 'mail.channel' &&
                threadViewer.thread.id === 20
            );
        },
    });
    assert.containsNone(
        document.body,
        '.o_Message',
        "should have initially no message in channel 20 matching the search 'test'"
    );

    await this.afterEvent({
        eventName: 'o-thread-view-hint-processed',
        func: () => {
            document.querySelector(`
                .o_DiscussSidebar_item[data-thread-local-id="${channel21.localId}"]
            `).click();
        },
        message: "should wait until channel 21 is loaded after clicking on it",
        predicate: ({ hint, threadViewer }) => {
            return (
                hint.type === 'messages-loaded' &&
                threadViewer.thread.model === 'mail.channel' &&
                threadViewer.thread.id === 21
            );
        },
    });
    assert.containsNone(
        document.body,
        '.o_Message',
        "should have no message in channel 21 matching the search 'test'"
    );
    // simulate receiving a message on channel 20 while channel 21 is displayed
    await this.env.services.rpc({
        route: '/mail/chat_post',
        params: {
            message_content: "test",
            uuid: channel20.uuid,
        },
    });
    assert.containsNone(
        document.body,
        '.o_Message',
        "should still have no message in channel 21 matching the search 'test' after receiving a message on channel 20"
    );

    await this.afterEvent({
        eventName: 'o-thread-view-hint-processed',
        func: () => {
            document.querySelector(`
                .o_DiscussSidebar_item[data-thread-local-id="${channel20.localId}"]
            `).click();
        },
        message: "should wait until channel 20 is loaded with the new message after clicking on it",
        predicate: ({ hint, threadViewer }) => {
            return (
                hint.type === 'messages-loaded' &&
                threadViewer.thread.model === 'mail.channel' &&
                threadViewer.thread.id === 20 &&
                threadViewer.threadCache.fetchedMessages.length === 1
            );
        },
    });
    assert.containsOnce(
        document.body,
        '.o_Message',
        "should now have the 1 message containing 'test' in channel 20 when displaying it, after having received the message while the channel was not visible"
    );
});

});
});
});
