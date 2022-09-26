/** @odoo-module **/

import { nextAnimationFrame, start, startServer } from '@mail/../tests/helpers/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('composer_suggestion_partner_tests.js');

QUnit.test('partner mention suggestion displayed', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({});
    pyEnv['res.partner'].create({
        email: "demo_user@odoo.com",
        im_status: 'online',
        name: 'Demo User',
    });
    const { env, insertText, openDiscuss } = await start({
        discuss: {
            params: {
                default_active_id: mailChannelId1,
            },
        },
        hasDiscuss: true,
        hasTimeControl: true,
    });
    await openDiscuss();
    await insertText('.o_ComposerTextInput_textarea', "@demo");
    await env.testUtils.advanceTime(300);
    await nextAnimationFrame();
    assert.containsOnce(
        document.body,
        `.o_ComposerSuggestion`,
        "Partner mention suggestion should be present"
    );
});

QUnit.test('partner mention suggestion correct data', async function (assert) {
    assert.expect(5);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({});
    pyEnv['res.partner'].create({
        email: "demo_user@odoo.com",
        im_status: 'online',
        name: 'Demo User',
    });
    const { env, insertText, openDiscuss } = await start({
        discuss: {
            params: {
                default_active_id: mailChannelId1,
            },
        },
        hasDiscuss: true,
        hasTimeControl: true,
    });
    await openDiscuss();
    await insertText('.o_ComposerTextInput_textarea', "@demo");
    await env.testUtils.advanceTime(300);
    await nextAnimationFrame();
    assert.containsOnce(
        document.querySelector('.o_ComposerSuggestion'),
        '.o_PartnerImStatusIcon',
        "Partner's im_status should be displayed"
    );
    assert.containsOnce(
        document.body,
        '.o_ComposerSuggestion_part1',
        "Partner's name should be present"
    );
    assert.strictEqual(
        document.querySelector('.o_ComposerSuggestion_part1').textContent,
        "Demo User",
        "Partner's name should be displayed"
    );
    assert.containsOnce(
        document.body,
        '.o_ComposerSuggestion_part2',
        "Partner's email should be present"
    );
    assert.strictEqual(
        document.querySelector('.o_ComposerSuggestion_part2').textContent,
        "(demo_user@odoo.com)",
        "Partner's email should be displayed"
    );
});

QUnit.test('partner mention suggestion active', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({});
    pyEnv['res.partner'].create({
        email: "demo_user@odoo.com",
        im_status: 'online',
        name: 'Demo User',
    });
    const { env, insertText, openDiscuss } = await start({
        discuss: {
            params: {
                default_active_id: mailChannelId1,
            },
        },
        hasDiscuss: true,
        hasTimeControl: true,
    });
    await openDiscuss();
    await insertText('.o_ComposerTextInput_textarea', "@demo");
    await env.testUtils.advanceTime(300);
    await nextAnimationFrame();
    assert.hasClass(
        document.querySelector('.o_ComposerSuggestion'),
        'active',
        "should be active initially"
    );
});

});
});
