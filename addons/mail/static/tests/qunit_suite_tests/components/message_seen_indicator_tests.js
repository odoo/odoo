/** @odoo-module **/

import { insert, insertAndReplace, link } from '@mail/model/model_field_command';
import {
    beforeEach,
    createRootMessagingComponent,
    start,
} from '@mail/../tests/helpers/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('message_seen_indicator_tests.js', {
    async beforeEach() {
        await beforeEach(this);

        this.createMessageSeenIndicatorComponent = async ({ message, target, thread }, otherProps) => {
            const props = Object.assign(
                { messageLocalId: message.localId, threadLocalId: thread.localId },
                otherProps
            );
            await createRootMessagingComponent(thread.env, "MessageSeenIndicator", {
                props,
                target,
            });
        };
    },
});

QUnit.test('rendering when just one has received the message', async function (assert) {
    assert.expect(3);

    const { messaging, widget } = await start({ data: this.data });
    const thread = messaging.models['Thread'].create({
        id: 1000,
        model: 'mail.channel',
        partnerSeenInfos: insertAndReplace([
            {
                lastFetchedMessage: insert({ id: 100 }),
                partner: insertAndReplace({ id: 10 }),
            },
            {
                partner: insertAndReplace({ id: 100 }),
            },
        ]),
        messageSeenIndicators: insertAndReplace({
            message: insertAndReplace({ id: 100 }),
        }),
    });
    const message = messaging.models['Message'].insert({
        author: insert({ id: messaging.currentPartner.id, display_name: "Demo User" }),
        body: "<p>Test</p>",
        id: 100,
        originThread: link(thread),
    });
    await this.createMessageSeenIndicatorComponent({ message, target: widget.el, thread });
    assert.containsOnce(
        document.body,
        '.o_MessageSeenIndicator',
        "should display a message seen indicator component"
    );
    assert.doesNotHaveClass(
        document.querySelector('.o_MessageSeenIndicator'),
        'o-all-seen',
        "indicator component should not be considered as all seen"
    );
    assert.containsOnce(
        document.body,
        '.o_MessageSeenIndicator_icon',
        "should display only one seen indicator icon"
    );
});

QUnit.test('rendering when everyone have received the message', async function (assert) {
    assert.expect(3);

    const { messaging, widget } = await start({ data: this.data });
    const thread = messaging.models['Thread'].create({
        id: 1000,
        model: 'mail.channel',
        partnerSeenInfos: insertAndReplace([
            {
                lastFetchedMessage: insert({ id: 100 }),
                partner: insertAndReplace({ id: 10 }),
            },
            {
                lastFetchedMessage: insert({ id: 99 }),
                partner: insertAndReplace({ id: 100 }),
            },
        ]),
        messageSeenIndicators: insertAndReplace({
            message: insertAndReplace({ id: 100 }),
        }),
    });
    const message = messaging.models['Message'].insert({
        author: insert({ id: messaging.currentPartner.id, display_name: "Demo User" }),
        body: "<p>Test</p>",
        id: 100,
        originThread: link(thread),
    });
    await this.createMessageSeenIndicatorComponent({ message, target: widget.el, thread });
    assert.containsOnce(
        document.body,
        '.o_MessageSeenIndicator',
        "should display a message seen indicator component"
    );
    assert.doesNotHaveClass(
        document.querySelector('.o_MessageSeenIndicator'),
        'o-all-seen',
        "indicator component should not be considered as all seen"
    );
    assert.containsOnce(
        document.body,
        '.o_MessageSeenIndicator_icon',
        "should display only one seen indicator icon"
    );
});

QUnit.test('rendering when just one has seen the message', async function (assert) {
    assert.expect(3);

    const { messaging, widget } = await start({ data: this.data });
    const thread = messaging.models['Thread'].create({
        id: 1000,
        model: 'mail.channel',
        partnerSeenInfos: insertAndReplace([
            {
                lastFetchedMessage: insert({ id: 100 }),
                lastSeenMessage: insert({ id: 100 }),
                partner: insertAndReplace({ id: 10 }),
            },
            {
                lastFetchedMessage: insert({ id: 99 }),
                partner: insertAndReplace({ id: 100 }),
            },
        ]),
        messageSeenIndicators: insertAndReplace({
            message: insertAndReplace({ id: 100 }),
        }),
    });
    const message = messaging.models['Message'].insert({
        author: insert({ id: messaging.currentPartner.id, display_name: "Demo User" }),
        body: "<p>Test</p>",
        id: 100,
        originThread: link(thread),
    });
    await this.createMessageSeenIndicatorComponent({ message, target: widget.el, thread });
    assert.containsOnce(
        document.body,
        '.o_MessageSeenIndicator',
        "should display a message seen indicator component"
    );
    assert.doesNotHaveClass(
        document.querySelector('.o_MessageSeenIndicator'),
        'o-all-seen',
        "indicator component should not be considered as all seen"
    );
    assert.containsN(
        document.body,
        '.o_MessageSeenIndicator_icon',
        2,
        "should display two seen indicator icon"
    );
});

QUnit.test('rendering when just one has seen & received the message', async function (assert) {
    assert.expect(3);

    const { messaging, widget } = await start({ data: this.data });
    const thread = messaging.models['Thread'].create({
        id: 1000,
        model: 'mail.channel',
        partnerSeenInfos: insertAndReplace([
            {
                lastFetchedMessage: insert({ id: 100 }),
                lastSeenMessage: insert({ id: 100 }),
                partner: insertAndReplace({ id: 10 }),
            },
            {
                partner: insertAndReplace({ id: 100 }),
            },
        ]),
        messageSeenIndicators: insertAndReplace({
            message: insertAndReplace({ id: 100 }),
        }),
    });
    const message = messaging.models['Message'].insert({
        author: insert({ id: messaging.currentPartner.id, display_name: "Demo User" }),
        body: "<p>Test</p>",
        id: 100,
        originThread: link(thread),
    });
    await this.createMessageSeenIndicatorComponent({ message, target: widget.el, thread });
    assert.containsOnce(
        document.body,
        '.o_MessageSeenIndicator',
        "should display a message seen indicator component"
    );
    assert.doesNotHaveClass(
        document.querySelector('.o_MessageSeenIndicator'),
        'o-all-seen',
        "indicator component should not be considered as all seen"
    );
    assert.containsN(
        document.body,
        '.o_MessageSeenIndicator_icon',
        2,
        "should display two seen indicator icon"
    );
});

QUnit.test('rendering when just everyone has seen the message', async function (assert) {
    assert.expect(3);

    const { messaging, widget } = await start({ data: this.data });
    const thread = messaging.models['Thread'].create({
        id: 1000,
        model: 'mail.channel',
        partnerSeenInfos: insertAndReplace([
            {
                lastFetchedMessage: insert({ id: 100 }),
                lastSeenMessage: insert({ id: 100 }),
                partner: insertAndReplace({ id: 10 }),
            },
            {
                lastFetchedMessage: insert({ id: 100 }),
                lastSeenMessage: insert({ id: 100 }),
                partner: insertAndReplace({ id: 100 }),
            },
        ]),
        messageSeenIndicators: insertAndReplace({
            message: insertAndReplace({ id: 100 }),
        }),
    });
    const message = messaging.models['Message'].insert({
        author: insert({ id: messaging.currentPartner.id, display_name: "Demo User" }),
        body: "<p>Test</p>",
        id: 100,
        originThread: link(thread),
    });
    await this.createMessageSeenIndicatorComponent({ message, target: widget.el, thread });
    assert.containsOnce(
        document.body,
        '.o_MessageSeenIndicator',
        "should display a message seen indicator component"
    );
    assert.hasClass(
        document.querySelector('.o_MessageSeenIndicator'),
        'o-all-seen',
        "indicator component should not considered as all seen"
    );
    assert.containsN(
        document.body,
        '.o_MessageSeenIndicator_icon',
        2,
        "should display two seen indicator icon"
    );
});

});
});
