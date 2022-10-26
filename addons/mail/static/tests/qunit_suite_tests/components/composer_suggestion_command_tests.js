/** @odoo-module **/

import { start, startServer } from '@mail/../tests/helpers/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('composer_suggestion_command_tests.js');

QUnit.test('command suggestion displayed', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({ name: 'my-channel' });
    const { insertText, openDiscuss } = await start({
        discuss: {
            params: {
                default_active_id: mailChannelId1,
            },
        },
    });
    await openDiscuss();
    await insertText('.o_ComposerTextInput_textarea', "/who");
    assert.containsOnce(
        document.body,
        '.o_ComposerSuggestionView',
        "Command suggestion should be present",
    );
});

QUnit.test('command suggestion correct data', async function (assert) {
    assert.expect(4);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({ name: 'my-channel' });
    const { insertText, openDiscuss } = await start({
        discuss: {
            params: {
                default_active_id: mailChannelId1,
            },
        },
    });
    await openDiscuss();
    await insertText('.o_ComposerTextInput_textarea', "/who");
    assert.containsOnce(
        document.body,
        '.o_ComposerSuggestionView_part1',
        "Command name should be present"
    );
    assert.strictEqual(
        document.querySelector(`.o_ComposerSuggestionView_part1`).textContent,
        "who",
        "Command name should be displayed"
    );
    assert.containsOnce(
        document.querySelector('.o_ComposerSuggestionView'),
        '.o_ComposerSuggestionView_part2',
        "Command help should be present"
    );
    assert.strictEqual(
        document.querySelector(`.o_ComposerSuggestionView_part2`).textContent,
        "List users in the current channel",
        "Command help should be displayed"
    );
});

QUnit.test('command suggestion active', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({ name: 'my-channel' });
    const { insertText, openDiscuss } = await start({
        discuss: {
            params: {
                default_active_id: mailChannelId1,
            },
        },
    });
    await openDiscuss();
    await insertText('.o_ComposerTextInput_textarea', "/who");
    assert.hasClass(
        document.querySelector('.o_ComposerSuggestionView'),
        'active',
        "1st suggestion should be active initially"
    );
});

});
});
