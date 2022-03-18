/** @odoo-module **/

import { start, startServer } from '@mail/../tests/helpers/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('composer_suggestion_channel_tests.js');

QUnit.test('channel mention suggestion displayed', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create();
    const { createComposerSuggestionComponent, messaging } = await start();
    const thread = messaging.models['Thread'].findFromIdentifyingData({
        id: mailChannelId1,
        model: 'mail.channel',
    });
    await createComposerSuggestionComponent(thread.composer, {
        isActive: true,
        modelName: 'Thread',
        recordLocalId: thread.localId,
    });

    assert.containsOnce(
        document.body,
        `.o_ComposerSuggestion`,
        "Channel mention suggestion should be present"
    );
});

QUnit.test('channel mention suggestion correct data', async function (assert) {
    assert.expect(3);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({ name: "General" });
    const { createComposerSuggestionComponent, messaging } = await start();
    const thread = messaging.models['Thread'].findFromIdentifyingData({
        id: mailChannelId1,
        model: 'mail.channel',
    });
    await createComposerSuggestionComponent(thread.composer, {
        isActive: true,
        modelName: 'Thread',
        recordLocalId: thread.localId,
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

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create();
    const { createComposerSuggestionComponent, messaging } = await start();
    const thread = messaging.models['Thread'].findFromIdentifyingData({
        id: mailChannelId1,
        model: 'mail.channel',
    });
    await createComposerSuggestionComponent(thread.composer, {
        isActive: true,
        modelName: 'Thread',
        recordLocalId: thread.localId,
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
