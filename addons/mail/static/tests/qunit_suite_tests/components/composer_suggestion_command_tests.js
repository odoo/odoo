/** @odoo-module **/

import { start, startServer } from '@mail/../tests/helpers/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('composer_suggestion_command_tests.js');

QUnit.test('command suggestion displayed', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create();
    const { createComposerSuggestionComponent, messaging } = await start();
    const thread = messaging.models['Thread'].findFromIdentifyingData({
        id: mailChannelId1,
        model: 'mail.channel',
    });
    const command = messaging.models['ChannelCommand'].create({
        methodName: '',
        name: 'whois',
        help: "Displays who it is",
    });
    await createComposerSuggestionComponent(thread.composer, {
        isActive: true,
        modelName: 'ChannelCommand',
        recordLocalId: command.localId,
    });

    assert.containsOnce(
        document.body,
        `.o_ComposerSuggestion`,
        "Command suggestion should be present"
    );
});

QUnit.test('command suggestion correct data', async function (assert) {
    assert.expect(5);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create();
    const { createComposerSuggestionComponent, messaging } = await start();
    const thread = messaging.models['Thread'].findFromIdentifyingData({
        id: mailChannelId1,
        model: 'mail.channel',
    });
    const command = messaging.models['ChannelCommand'].create({
        methodName: '',
        name: 'whois',
        help: "Displays who it is",
    });
    await createComposerSuggestionComponent(thread.composer, {
        isActive: true,
        modelName: 'ChannelCommand',
        recordLocalId: command.localId,
    });

    assert.containsOnce(
        document.body,
        '.o_ComposerSuggestion',
        "Command suggestion should be present"
    );
    assert.containsOnce(
        document.body,
        '.o_ComposerSuggestion_part1',
        "Command name should be present"
    );
    assert.strictEqual(
        document.querySelector(`.o_ComposerSuggestion_part1`).textContent,
        "whois",
        "Command name should be displayed"
    );
    assert.containsOnce(
        document.body,
        '.o_ComposerSuggestion_part2',
        "Command help should be present"
    );
    assert.strictEqual(
        document.querySelector(`.o_ComposerSuggestion_part2`).textContent,
        "Displays who it is",
        "Command help should be displayed"
    );
});

QUnit.test('command suggestion active', async function (assert) {
    assert.expect(2);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create();
    const { createComposerSuggestionComponent, messaging } = await start();
    const thread = messaging.models['Thread'].findFromIdentifyingData({
        id: mailChannelId1,
        model: 'mail.channel',
    });
    const command = messaging.models['ChannelCommand'].create({
        methodName: '',
        name: 'whois',
        help: "Displays who it is",
    });
    await createComposerSuggestionComponent(thread.composer, {
        isActive: true,
        modelName: 'ChannelCommand',
        recordLocalId: command.localId,
    });

    assert.containsOnce(
        document.body,
        '.o_ComposerSuggestion',
        "Command suggestion should be displayed"
    );
    assert.hasClass(
        document.querySelector('.o_ComposerSuggestion'),
        'active',
        "should be active initially"
    );
});

});
});
