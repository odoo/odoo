/** @odoo-module **/

import { start, startServer } from '@mail/../tests/helpers/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('composer_suggestion_canned_response_tests.js');

QUnit.test('canned response suggestion displayed', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({});
    pyEnv['mail.shortcode'].create({
        source: 'hello',
        substitution: "Hello, how are you?",
    });
    const { insertText, openDiscuss } = await start({
        discuss: {
            params: {
                default_active_id: mailChannelId1,
            },
        },
    });
    await openDiscuss();
    await insertText('.o_ComposerTextInput_textarea', ":hello");
    assert.containsOnce(
        document.body,
        `.o_ComposerSuggestionView`,
        "Canned response suggestion should be present"
    );
});

QUnit.test('canned response suggestion correct data', async function (assert) {
    assert.expect(4);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({});
    pyEnv['mail.shortcode'].create({
        source: 'hello',
        substitution: "Hello, how are you?",
    });
    const { insertText, openDiscuss } = await start({
        discuss: {
            params: {
                default_active_id: mailChannelId1,
            },
        },
    });
    await openDiscuss();
    await insertText('.o_ComposerTextInput_textarea', ":hello");
    assert.containsOnce(
        document.body,
        '.o_ComposerSuggestionView_part1',
        "Canned response source should be present"
    );
    assert.strictEqual(
        document.querySelector(`.o_ComposerSuggestionView_part1`).textContent,
        "hello",
        "Canned response source should be displayed"
    );
    assert.containsOnce(
        document.body,
        '.o_ComposerSuggestionView_part2',
        "Canned response substitution should be present"
    );
    assert.strictEqual(
        document.querySelector(`.o_ComposerSuggestionView_part2`).textContent,
        "Hello, how are you?",
        "Canned response substitution should be displayed"
    );
});

QUnit.test('canned response suggestion active', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({});
    pyEnv['mail.shortcode'].create({
        source: 'hello',
        substitution: "Hello, how are you?",
    });
    const { insertText, openDiscuss } = await start({
        discuss: {
            params: {
                default_active_id: mailChannelId1,
            },
        },
    });
    await openDiscuss();
    await insertText('.o_ComposerTextInput_textarea', ":hello");
    assert.hasClass(
        document.querySelector('.o_ComposerSuggestionView'),
        'active',
        "should be active initially"
    );
});

});
});
