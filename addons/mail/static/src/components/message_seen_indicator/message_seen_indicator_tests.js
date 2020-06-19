odoo.define('mail/static/src/components/message_seen_indicator/message_seen_indicator_tests', function (require) {
'use strict';

const components = {
    MessageSendIndicator: require('mail/static/src/components/message_seen_indicator/message_seen_indicator.js'),
};
const {
    afterEach: utilsAfterEach,
    beforeEach: utilsBeforeEach,
    start: utilsStart,
} = require('mail/static/src/utils/test_utils.js');

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('message_seen_indicator', {}, function () {
QUnit.module('message_seen_indicator_tests.js', {
    beforeEach() {
        utilsBeforeEach(this);

        this.createMessageSeenIndicatorComponent = async ({ message, thread }, otherProps) => {
            const MessageSeenIndicatorComponent = components.MessageSendIndicator;
            MessageSeenIndicatorComponent.env = this.env;
            this.component = new MessageSeenIndicatorComponent(null, Object.assign({
                messageLocalId: message.localId,
                threadLocalId: thread.localId,
            }, otherProps));
            await this.component.mount(this.widget.el);
        };

        this.start = async params => {
            if (this.widget) {
                this.widget.destroy();
            }
            let { env, widget } = await utilsStart(Object.assign({}, params, {
                data: this.data,
            }));
            this.env = env;
            this.widget = widget;
        };
    },
    afterEach() {
        utilsAfterEach(this);
        if (this.component) {
            this.component.destroy();
        }
        if (this.widget) {
            this.widget.destroy();
        }
        this.env = undefined;
        delete components.MessageSendIndicator.env;
    },
});

QUnit.test('rendering when just one has received the message', async function (assert) {
    assert.expect(3);

    await this.start();
    const thread = this.env.models['mail.thread'].create({
        id: 1000,
        model: 'mail.channel',
        partnerSeenInfos: [['create', [
            {
                partner: [['create', {id: 10}]],
                lastFetchedMessage: [['insert', {id: 100}]]
            },
            {
                partner: [['create', {id: 100}]],
            },
        ]]],
        messageSeenIndicators: [['insert', {
            id: this.env.models['mail.message_seen_indicator'].computeId(100, 1000),
            message: [['insert', {id: 100}]],
        }]],
    });
    const message = this.env.models['mail.message'].create({
        author: [['insert', { id: this.env.session.partner_id, display_name: "Demo User" }]],
        body: "<p>Test</p>",
        id: 100,
        threadCaches: [['link', thread.mainCache]],
    });
    await this.createMessageSeenIndicatorComponent({message, thread});
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
        id: 1000,
        model: 'mail.channel',
        partnerSeenInfos: [['create', [
            {
                partner: [['create', {id: 10}]],
                lastFetchedMessage: [['insert', {id: 100}]],
            },
            {
                partner: [['create', {id: 100}]],
                lastFetchedMessage: [['insert', {id: 99}]],
            },
        ]]],
        messageSeenIndicators: [['insert', {
            id: this.env.models['mail.message_seen_indicator'].computeId(100, 1000),
            message: [['insert', {id: 100}]],
        }]],
    });
    const message = this.env.models['mail.message'].create({
        author: [['insert', { id: this.env.session.partner_id, display_name: "Demo User" }]],
        body: "<p>Test</p>",
        id: 100,
        threadCaches: [['link', thread.mainCache]],
    });
    await this.createMessageSeenIndicatorComponent({message, thread});
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
        id: 1000,
        model: 'mail.channel',
        partnerSeenInfos: [['create', [
            {
                partner: [['create', {id: 10}]],
                lastFetchedMessage: [['insert', {id: 100}]],
                lastSeenMessage: [['insert', {id: 100}]],
            },
            {
                partner: [['create', {id: 100}]],
                lastFetchedMessage: [['insert', {id: 99}]],
            },
        ]]],
        messageSeenIndicators: [['insert', {
            id: this.env.models['mail.message_seen_indicator'].computeId(100, 1000),
            message: [['insert', {id: 100}]],
        }]],
    });
    const message = this.env.models['mail.message'].create({
        author: [['insert', { id: this.env.session.partner_id, display_name: "Demo User" }]],
        body: "<p>Test</p>",
        id: 100,
        threadCaches: [['link', thread.mainCache]],
    });
    await this.createMessageSeenIndicatorComponent({message, thread});
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
        id: 1000,
        model: 'mail.channel',
        partnerSeenInfos: [['create', [
            {
                partner: [['create', {id: 10}]],
                lastFetchedMessage: [['insert', {id: 100}]],
                lastSeenMessage: [['insert', {id: 100}]],
            },
            {
                partner: [['create', {id: 100}]],
            },
        ]]],
        messageSeenIndicators: [['insert', {
            id: this.env.models['mail.message_seen_indicator'].computeId(100, 1000),
            message: [['insert', {id: 100}]],
        }]],
    });
    const message = this.env.models['mail.message'].create({
        author: [['insert', { id: this.env.session.partner_id, display_name: "Demo User" }]],
        body: "<p>Test</p>",
        id: 100,
        threadCaches: [['link', thread.mainCache]],
    });
    await this.createMessageSeenIndicatorComponent({message, thread});
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
        id: 1000,
        model: 'mail.channel',
        partnerSeenInfos: [['create', [
            {
                partner: [['create', {id: 10}]],
                lastFetchedMessage: [['insert', {id: 100}]],
                lastSeenMessage: [['insert', {id: 100}]],
            },
            {
                partner: [['create', {id: 100}]],
                lastFetchedMessage: [['insert', {id: 100}]],
                lastSeenMessage: [['insert', {id: 100}]],
            },
        ]]],
        messageSeenIndicators: [['insert', {
            id: this.env.models['mail.message_seen_indicator'].computeId(100, 1000),
            message: [['insert', {id: 100}]],
        }]],
    });
    const message = this.env.models['mail.message'].create({
        author: [['insert', { id: this.env.session.partner_id, display_name: "Demo User" }]],
        body: "<p>Test</p>",
        id: 100,
        threadCaches: [['link', thread.mainCache]],
    });
    await this.createMessageSeenIndicatorComponent({message, thread});
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
