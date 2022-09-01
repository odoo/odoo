/** @odoo-module **/

import { start, startServer } from '@mail/../tests/helpers/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('composer_suggestion_partner_tests.js');

QUnit.test('partner mention suggestion displayed', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const resPartnerId = pyEnv['res.partner'].create({
        email: "demo_user@odoo.com",
        im_status: 'online',
        name: 'Demo User',
    });
    const mailChannelId1 = pyEnv['mail.channel'].create({
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: resPartnerId }],
        ],
    });
    const { insertText, openDiscuss } = await start({
        discuss: {
            params: {
                default_active_id: mailChannelId1,
            },
        },
    });
    await openDiscuss();
    await insertText('.o_ComposerTextInput_textarea', "@demo");
    assert.containsOnce(
        document.body,
        `.o_ComposerSuggestionView`,
        "Partner mention suggestion should be present"
    );
});

QUnit.test('partner mention suggestion correct data', async function (assert) {
    assert.expect(5);

    const pyEnv = await startServer();
    const resPartnerId = pyEnv['res.partner'].create({
        email: "demo_user@odoo.com",
        im_status: 'online',
        name: 'Demo User',
    });
    const mailChannelId1 = pyEnv['mail.channel'].create({
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: resPartnerId }],
        ],
    });
    const { insertText, openDiscuss } = await start({
        discuss: {
            params: {
                default_active_id: mailChannelId1,
            },
        },
    });
    await openDiscuss();
    await insertText('.o_ComposerTextInput_textarea', "@demo");
    assert.containsOnce(
        document.querySelector('.o_ComposerSuggestionView'),
        '.o_PersonaImStatusIcon',
        "Partner's im_status should be displayed"
    );
    assert.containsOnce(
        document.body,
        '.o_ComposerSuggestionView_part1',
        "Partner's name should be present"
    );
    assert.strictEqual(
        document.querySelector('.o_ComposerSuggestionView_part1').textContent,
        "Demo User",
        "Partner's name should be displayed"
    );
    assert.containsOnce(
        document.body,
        '.o_ComposerSuggestionView_part2',
        "Partner's email should be present"
    );
    assert.strictEqual(
        document.querySelector('.o_ComposerSuggestionView_part2').textContent,
        "(demo_user@odoo.com)",
        "Partner's email should be displayed"
    );
});

QUnit.test('partner mention suggestion active', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const resPartnerId = pyEnv['res.partner'].create({
        email: "demo_user@odoo.com",
        im_status: 'online',
        name: 'Demo User',
    });
    const mailChannelId1 = pyEnv['mail.channel'].create({
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: resPartnerId }],
        ],
    });
    const { insertText, openDiscuss } = await start({
        discuss: {
            params: {
                default_active_id: mailChannelId1,
            },
        },
    });
    await openDiscuss();
    await insertText('.o_ComposerTextInput_textarea', "@demo");
    assert.hasClass(
        document.querySelector('.o_ComposerSuggestionView'),
        'active',
        "should be active initially"
    );
});

});
});
