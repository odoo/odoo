odoo.define('mail/static/src/components/suggestions_list/composer_suggestion_command_tests.js', function (require) {
'use strict';

const components = {
    ComposerSuggestion: require('mail/static/src/components/suggestion/suggestion.js'),
};
const {
    afterEach,
    beforeEach,
    createRootComponent,
    start,
} = require('mail/static/src/utils/test_utils.js');

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('suggestion', {}, function () {
QUnit.module('suggestion_command_tests.js', {
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

QUnit.test('command suggestion displayed', async function (assert) {
    assert.expect(1);

    this.data['mail.channel'].records.push({ id: 20 });
    await this.start();
    const thread = this.env.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel',
    });
    const command = this.env.models['mail.channel_command'].create({
        name: 'whois',
        help: "Displays who it is",
    });
    await this.createComposerSuggestion({
        suggestionManagerLocalId: thread.composer.suggestionManager.localId,
        isActive: true,
        modelName: 'mail.channel_command',
        recordLocalId: command.localId,
    });

    assert.containsOnce(
        document.body,
        `.o_Suggestion`,
        "Command suggestion should be present"
    );
});

QUnit.test('command suggestion correct data', async function (assert) {
    assert.expect(5);

    this.data['mail.channel'].records.push({ id: 20 });
    await this.start();
    const thread = this.env.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel',
    });
    const command = this.env.models['mail.channel_command'].create({
        name: 'whois',
        help: "Displays who it is",
    });
    await this.createComposerSuggestion({
        suggestionManagerLocalId: thread.composer.suggestionManager.localId,
        isActive: true,
        modelName: 'mail.channel_command',
        recordLocalId: command.localId,
    });

    assert.containsOnce(
        document.body,
        '.o_Suggestion',
        "Command suggestion should be present"
    );
    assert.containsOnce(
        document.body,
        '.o_Suggestion_part1',
        "Command name should be present"
    );
    assert.strictEqual(
        document.querySelector(`.o_Suggestion_part1`).textContent,
        "whois",
        "Command name should be displayed"
    );
    assert.containsOnce(
        document.body,
        '.o_Suggestion_part2',
        "Command help should be present"
    );
    assert.strictEqual(
        document.querySelector(`.o_Suggestion_part2`).textContent,
        "Displays who it is",
        "Command help should be displayed"
    );
});

QUnit.test('command suggestion active', async function (assert) {
    assert.expect(2);

    this.data['mail.channel'].records.push({ id: 20 });
    await this.start();
    const thread = this.env.models['mail.thread'].findFromIdentifyingData({
        id: 20,
        model: 'mail.channel',
    });
    const command = this.env.models['mail.channel_command'].create({
        name: 'whois',
        help: "Displays who it is",
    });
    await this.createComposerSuggestion({
        suggestionManagerLocalId: thread.composer.suggestionManager.localId,
        isActive: true,
        modelName: 'mail.channel_command',
        recordLocalId: command.localId,
    });

    assert.containsOnce(
        document.body,
        '.o_Suggestion',
        "Command suggestion should be displayed"
    );
    assert.hasClass(
        document.querySelector('.o_Suggestion'),
        'active',
        "should be active initially"
    );
});

});
});
});

});
