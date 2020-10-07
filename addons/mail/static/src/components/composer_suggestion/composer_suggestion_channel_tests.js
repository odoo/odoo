odoo.define('mail/static/src/components/composer_suggestion/composer_suggestion_channel_tests.js', function (require) {
'use strict';

const components = {
    ComposerSuggestion: require('mail/static/src/components/composer_suggestion/composer_suggestion.js'),
};
const {
    afterEach,
    beforeEach,
    createRootComponent,
    start,
} = require('mail/static/src/utils/test_utils.js');

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('composer_suggestion', {}, function () {
QUnit.module('composer_suggestion_channel_tests.js', {
    beforeEach() {
        beforeEach(this);

        this.createComposerSuggestion = async props => {
            await createRootComponent(this, components.ComposerSuggestion, {
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

QUnit.test('channel mention suggestion displayed', async function (assert) {
    assert.expect(1);

    this.data['mail.channel'].records.push({ id: 20 });
    await this.start();
    const thread = this.env.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel',
    });
    const channel = this.env.models['mail.thread'].create({
        id: 7,
        name: "General",
        model: 'mail.channel',
    });
    await this.createComposerSuggestion({
        composerLocalId: thread.composer.localId,
        isActive: true,
        modelName: 'mail.thread',
        recordLocalId: channel.localId,
    });

    assert.containsOnce(
        document.body,
        `.o_ComposerSuggestion`,
        "Channel mention suggestion should be present"
    );
});

QUnit.test('channel mention suggestion correct data', async function (assert) {
    assert.expect(3);

    this.data['mail.channel'].records.push({ id: 20 });
    await this.start();
    const thread = this.env.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel',
    });
    const channel = this.env.models['mail.thread'].create({
        id: 7,
        name: "General",
        model: 'mail.channel',
    });
    await this.createComposerSuggestion({
        composerLocalId: thread.composer.localId,
        isActive: true,
        modelName: 'mail.thread',
        recordLocalId: channel.localId,
    });

    assert.containsOnce(
        document.body,
        '.o_ComposerSuggestion',
        "Channel mention suggestion should be present"
    );
    assert.containsOnce(
        document.body,
        '.o_ComposerSuggestion_part1',
        "Channel name should be present"
    );
    assert.strictEqual(
        document.querySelector(`.o_ComposerSuggestion_part1`).textContent,
        "General",
        "Channel name should be displayed"
    );
});

QUnit.test('channel mention suggestion active', async function (assert) {
    assert.expect(2);

    this.data['mail.channel'].records.push({ id: 20 });
    await this.start();
    const thread = this.env.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel',
    });
    const channel = this.env.models['mail.thread'].create({
        id: 7,
        name: "General",
        model: 'mail.channel',
    });
    await this.createComposerSuggestion({
        composerLocalId: thread.composer.localId,
        isActive: true,
        modelName: 'mail.thread',
        recordLocalId: channel.localId,
    });

    assert.containsOnce(
        document.body,
        '.o_ComposerSuggestion',
        "Channel mention suggestion should be displayed"
    );
    assert.hasClass(
        document.querySelector('.o_ComposerSuggestion'),
        'active',
        "should be active initially"
    );
});

});
});
});

});
