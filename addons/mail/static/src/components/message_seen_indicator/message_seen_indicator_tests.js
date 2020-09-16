odoo.define('mail/static/src/components/message_seen_indicator/message_seen_indicator_tests', function (require) {
'use strict';

const components = {
    MessageSendIndicator: require('mail/static/src/components/message_seen_indicator/message_seen_indicator.js'),
};
const {
    afterEach,
    beforeEach,
    createRootComponent,
    start,
} = require('mail/static/src/utils/test_utils.js');

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('message_seen_indicator', {}, function () {
QUnit.module('message_seen_indicator_tests.js', {
    beforeEach() {
        beforeEach(this);

        this.createMessageSeenIndicatorComponent = async ({ message, thread }, otherProps) => {
            const props = Object.assign(
                { messageLocalId: message.localId, threadLocalId: thread.localId },
                otherProps
            );
            await createRootComponent(this, components.MessageSendIndicator, {
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

QUnit.test('rendering when just one has received the message', async function (assert) {
    assert.expect(3);

    await this.start();
    const thread = this.env.models['mail.thread'].create({
        __mfield_id: 1000,
        __mfield_model: 'mail.channel',
        __mfield_partnerSeenInfos: [['create', [
            {
                __mfield_channelId: 1000,
                __mfield_lastFetchedMessage: [['insert', {
                    __mfield_id: 100,
                }]],
                __mfield_partnerId: 10,
            },
            {
                __mfield_channelId: 1000,
                __mfield_partnerId: 100,
            },
        ]]],
        __mfield_messageSeenIndicators: [['insert', {
            __mfield_channelId: 1000,
            __mfield_messageId: 100,
        }]],
    });
    const message = this.env.models['mail.message'].insert({
        __mfield_author: [['insert', {
            __mfield_id: this.env.messaging.__mfield_currentPartner().__mfield_id(),
            __mfield_display_name: "Demo User",
        }]],
        __mfield_body: "<p>Test</p>",
        __mfield_id: 100,
        __mfield_originThread: [['link', thread]],
    });
    await this.createMessageSeenIndicatorComponent({ message, thread });
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

    await this.start();
    const thread = this.env.models['mail.thread'].create({
        __mfield_id: 1000,
        __mfield_model: 'mail.channel',
        __mfield_partnerSeenInfos: [['create', [
            {
                __mfield_channelId: 1000,
                __mfield_lastFetchedMessage: [['insert', {
                    __mfield_id: 100,
                }]],
                __mfield_partnerId: 10,
            },
            {
                __mfield_channelId: 1000,
                __mfield_lastFetchedMessage: [['insert', {
                    __mfield_id: 99,
                }]],
                __mfield_partnerId: 100,
            },
        ]]],
        __mfield_messageSeenIndicators: [['insert', {
            __mfield_channelId: 1000,
            __mfield_messageId: 100,
        }]],
    });
    const message = this.env.models['mail.message'].insert({
        __mfield_author: [['insert', {
            __mfield_id: this.env.messaging.__mfield_currentPartner().__mfield_id(),
            __mfield_display_name: "Demo User",
        }]],
        __mfield_body: "<p>Test</p>",
        __mfield_id: 100,
        __mfield_originThread: [['link', thread]],
    });
    await this.createMessageSeenIndicatorComponent({ message, thread });
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

    await this.start();
    const thread = this.env.models['mail.thread'].create({
        __mfield_id: 1000,
        __mfield_model: 'mail.channel',
        __mfield_partnerSeenInfos: [['create', [
            {
                __mfield_channelId: 1000,
                __mfield_lastFetchedMessage: [['insert', {
                    __mfield_id: 100,
                }]],
                __mfield_lastSeenMessage: [['insert', {
                    __mfield_id: 100,
                }]],
                __mfield_partnerId: 10,
            },
            {
                __mfield_channelId: 1000,
                __mfield_lastFetchedMessage: [['insert', {
                    __mfield_id: 99,
                }]],
                __mfield_partnerId: 100,
            },
        ]]],
        __mfield_messageSeenIndicators: [['insert', {
            __mfield_channelId: 1000,
            __mfield_messageId: 100,
        }]],
    });
    const message = this.env.models['mail.message'].insert({
        __mfield_author: [['insert', {
            __mfield_id: this.env.messaging.__mfield_currentPartner(this).__mfield_id(this),
            __mfield_display_name: "Demo User",
        }]],
        __mfield_body: "<p>Test</p>",
        __mfield_id: 100,
        __mfield_originThread: [['link', thread]],
    });
    await this.createMessageSeenIndicatorComponent({ message, thread });
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

    await this.start();
    const thread = this.env.models['mail.thread'].create({
        __mfield_id: 1000,
        __mfield_model: 'mail.channel',
        __mfield_partnerSeenInfos: [['create', [
            {
                __mfield_channelId: 1000,
                __mfield_lastFetchedMessage: [['insert', {
                    __mfield_id: 100,
                }]],
                __mfield_lastSeenMessage: [['insert', {
                    __mfield_id: 100,
                }]],
                __mfield_partnerId: 10,
            },
            {
                __mfield_channelId: 1000,
                __mfield_partnerId: 100,
            },
        ]]],
        __mfield_messageSeenIndicators: [['insert', {
            __mfield_channelId: 1000,
            __mfield_messageId: 100,
        }]],
    });
    const message = this.env.models['mail.message'].insert({
        __mfield_author: [['insert', {
            __mfield_id: this.env.messaging.__mfield_currentPartner(this).__mfield_id(this),
            __mfield_display_name: "Demo User",
        }]],
        __mfield_body: "<p>Test</p>",
        __mfield_id: 100,
        __mfield_originThread: [['link', thread]],
    });
    await this.createMessageSeenIndicatorComponent({ message, thread });
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

    await this.start();
    const thread = this.env.models['mail.thread'].create({
        __mfield_id: 1000,
        __mfield_model: 'mail.channel',
        __mfield_partnerSeenInfos: [['create', [
            {
                __mfield_channelId: 1000,
                __mfield_lastFetchedMessage: [['insert', {
                    __mfield_id: 100,
                }]],
                __mfield_lastSeenMessage: [['insert', {
                    __mfield_id: 100,
                }]],
                __mfield_partnerId: 10,
            },
            {
                __mfield_channelId: 1000,
                __mfield_lastFetchedMessage: [['insert', {
                    __mfield_id: 100,
                }]],
                __mfield_lastSeenMessage: [['insert', {
                    __mfield_id: 100,
                }]],
                __mfield_partnerId: 100,
            },
        ]]],
        __mfield_messageSeenIndicators: [['insert', {
            __mfield_channelId: 1000,
            __mfield_messageId: 100,
        }]],
    });
    const message = this.env.models['mail.message'].insert({
        __mfield_author: [['insert', {
            __mfield_id: this.env.messaging.__mfield_currentPartner(this).__mfield_id(this),
            __mfield_display_name: "Demo User",
        }]],
        __mfield_body: "<p>Test</p>",
        __mfield_id: 100,
        __mfield_originThread: [['link', thread]],
    });
    await this.createMessageSeenIndicatorComponent({ message, thread });
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
});

});
