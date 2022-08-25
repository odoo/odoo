/** @odoo-module **/

import { start, startServer } from '@mail/../tests/helpers/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('composer_suggestion_channel_tests.js');

QUnit.test('channel mention suggestion displayed', async function (assert) {
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
    await insertText('.o_ComposerTextInput_textarea', "#my-channel");
    assert.containsOnce(
        document.body,
        `.o_ComposerSuggestionView`,
        "Channel mention suggestion should be present"
    );
});

QUnit.test('channel mention suggestion correct data', async function (assert) {
    assert.expect(2);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({ name: "General" });
    const { insertText, openDiscuss } = await start({
        discuss: {
            params: {
                default_active_id: mailChannelId1,
            },
        },
    });
    await openDiscuss();
    await insertText('.o_ComposerTextInput_textarea', "#General");
    assert.containsOnce(
        document.body,
        '.o_ComposerSuggestionView_part1',
        "Channel name should be present"
    );
    assert.strictEqual(
        document.querySelector(`.o_ComposerSuggestionView_part1`).textContent,
        "General",
        "Channel name should be displayed"
    );
});

QUnit.test('channel mention suggestion active', async function (assert) {
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
    await insertText('.o_ComposerTextInput_textarea', "#my-channel");
    assert.hasClass(
        document.querySelector('.o_ComposerSuggestionView'),
        'active',
        "should be active initially"
    );
});

});
});
