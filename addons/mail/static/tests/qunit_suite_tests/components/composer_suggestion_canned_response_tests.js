/** @odoo-module **/

import { start, startServer } from '@mail/../tests/helpers/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('composer_suggestion_canned_response_tests.js');

QUnit.test('canned response suggestion displayed', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create();
    const { createComposerSuggestionComponent, messaging } = await start();
    const thread = messaging.models['Thread'].findFromIdentifyingData({
        id: mailChannelId1,
        model: 'mail.channel',
    });
    const cannedResponse = messaging.models['CannedResponse'].create({
        id: 7,
        source: 'hello',
        substitution: "Hello, how are you?",
    });
    await createComposerSuggestionComponent(thread.composer, {
        isActive: true,
        modelName: 'CannedResponse',
        recordLocalId: cannedResponse.localId,
    });

    assert.containsOnce(
        document.body,
        `.o_ComposerSuggestion`,
        "Canned response suggestion should be present"
    );
});

QUnit.test('canned response suggestion correct data', async function (assert) {
    assert.expect(5);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create();
    const { createComposerSuggestionComponent, messaging } = await start();
    const thread = messaging.models['Thread'].findFromIdentifyingData({
        id: mailChannelId1,
        model: 'mail.channel',
    });
    const cannedResponse = messaging.models['CannedResponse'].create({
        id: 7,
        source: 'hello',
        substitution: "Hello, how are you?",
    });
    await createComposerSuggestionComponent(thread.composer, {
        isActive: true,
        modelName: 'CannedResponse',
        recordLocalId: cannedResponse.localId,
    });

    assert.containsOnce(
        document.body,
        '.o_ComposerSuggestion',
        "Canned response suggestion should be present"
    );
    assert.containsOnce(
        document.body,
        '.o_ComposerSuggestion_part1',
        "Canned response source should be present"
    );
    assert.strictEqual(
        document.querySelector(`.o_ComposerSuggestion_part1`).textContent,
        "hello",
        "Canned response source should be displayed"
    );
    assert.containsOnce(
        document.body,
        '.o_ComposerSuggestion_part2',
        "Canned response substitution should be present"
    );
    assert.strictEqual(
        document.querySelector(`.o_ComposerSuggestion_part2`).textContent,
        "Hello, how are you?",
        "Canned response substitution should be displayed"
    );
});

QUnit.test('canned response suggestion active', async function (assert) {
    assert.expect(2);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create();
    const { createComposerSuggestionComponent, messaging } = await start();
    const thread = messaging.models['Thread'].findFromIdentifyingData({
        id: mailChannelId1,
        model: 'mail.channel',
    });
    const cannedResponse = messaging.models['CannedResponse'].create({
        id: 7,
        source: 'hello',
        substitution: "Hello, how are you?",
    });
    await createComposerSuggestionComponent(thread.composer, {
        isActive: true,
        modelName: 'CannedResponse',
        recordLocalId: cannedResponse.localId,
    });

    assert.containsOnce(
        document.body,
        '.o_ComposerSuggestion',
        "Canned response suggestion should be displayed"
    );
    assert.hasClass(
        document.querySelector('.o_ComposerSuggestion'),
        'active',
        "should be active initially"
    );
});

});
});
