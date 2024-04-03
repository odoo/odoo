/** @odoo-module **/

import {
    start,
    startServer,
} from '@mail/../tests/helpers/test_utils';

QUnit.module('website_livechat', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('discuss_tests.js');

QUnit.test('rendering of visitor banner', async function (assert) {
    assert.expect(13);

    const pyEnv = await startServer();
    const resCountryId1 = pyEnv['res.country'].create({
        code: 'FAKE',
    });
    const websiteVisitorId1 = pyEnv['website.visitor'].create({
        country_id: resCountryId1,
        display_name: 'Visitor #11',
        history: 'Home → Contact',
        is_connected: true,
        lang_name: "English",
        website_name: "General website",
    });
    const mailChannelId1 = pyEnv['mail.channel'].create({
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: pyEnv.publicPartnerId }],
        ],
        channel_type: 'livechat',
        livechat_operator_id: pyEnv.currentPartnerId,
        livechat_visitor_id: websiteVisitorId1,
    });
    const { openDiscuss } = await start({
        discuss: {
            context: {
                active_id: `mail.channel_${mailChannelId1}`,
            },
        },
    });
    await openDiscuss();
    assert.containsOnce(
        document.body,
        '.o_VisitorBanner',
        "should have a visitor banner",
    );
    assert.containsOnce(
        document.body,
        '.o_VisitorBanner_avatar',
        "should show the visitor avatar in the banner",
    );
    assert.strictEqual(
        document.querySelector('.o_VisitorBanner_avatar').dataset.src,
        "/mail/static/src/img/smiley/avatar.jpg",
        "should show the default avatar",
    );
    assert.containsOnce(
        document.body,
        '.o_VisitorBanner_onlineStatusIcon',
        "should show the visitor online status icon on the avatar",
    );
    assert.strictEqual(
        document.querySelector('.o_VisitorBanner_country').dataset.src,
        "/base/static/img/country_flags/FAKE.png",
        "should show the flag of the country of the visitor",
    );
    assert.containsOnce(
        document.body,
        '.o_VisitorBanner_visitor',
        "should show the visitor name in the banner",
    );
    assert.strictEqual(
        document.querySelector('.o_VisitorBanner_visitor').textContent,
        "Visitor #11",
        "should have 'Visitor #11' as visitor name",
    );
    assert.containsOnce(
        document.body,
        '.o_VisitorBanner_language',
        "should show the visitor language in the banner",
    );
    assert.strictEqual(
        document.querySelector('.o_VisitorBanner_language').textContent,
        "English",
        "should have 'English' as language of the visitor",
    );
    assert.containsOnce(
        document.body,
        '.o_VisitorBanner_website',
        "should show the visitor website in the banner",
    );
    assert.strictEqual(
        document.querySelector('.o_VisitorBanner_website').textContent,
        "General website",
        "should have 'General website' as website of the visitor",
    );
    assert.containsOnce(
        document.body,
        '.o_VisitorBanner_history',
        "should show the visitor history in the banner",
    );
    assert.strictEqual(
        document.querySelector('.o_VisitorBanner_history').textContent,
        "Home → Contact",
        "should have 'Home → Contact' as history of the visitor",
    );
});

QUnit.test('livechat with non-logged visitor should show visitor banner', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const resCountryId1 = pyEnv['res.country'].create({
        code: 'FAKE',
    });
    const websiteVisitorId1 = pyEnv['website.visitor'].create({
        country_id: resCountryId1,
        display_name: 'Visitor #11',
        history: 'Home → Contact',
        is_connected: true,
        lang_name: "English",
        website_name: "General website",
    });
    const mailChannelId1 = pyEnv['mail.channel'].create({
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: pyEnv.publicPartnerId }],
        ],
        channel_type: 'livechat',
        livechat_operator_id: pyEnv.currentPartnerId,
        livechat_visitor_id: websiteVisitorId1,
    });
    const { openDiscuss } = await start({
        discuss: {
            context: {
                active_id: `mail.channel_${mailChannelId1}`,
            },
        },
    });
    await openDiscuss();
    assert.containsOnce(
        document.body,
        '.o_VisitorBanner',
        "should have a visitor banner",
    );
});

QUnit.test('livechat with logged visitor should show visitor banner', async function (assert) {
    assert.expect(2);

    const pyEnv = await startServer();
    const resCountryId1 = pyEnv['res.country'].create({
        code: 'FAKE',
    });
    const resPartnerId1 = pyEnv['res.partner'].create({
        name: 'Partner Visitor',
    });
    const websiteVisitorId1 = pyEnv['website.visitor'].create({
        country_id: resCountryId1,
        display_name: 'Visitor #11',
        history: 'Home → Contact',
        is_connected: true,
        lang_name: "English",
        partner_id: resPartnerId1,
        website_name: "General website",
    });
    const mailChannelId1 = pyEnv['mail.channel'].create({
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: resPartnerId1 }],
        ],
        channel_type: 'livechat',
        livechat_operator_id: pyEnv.currentPartnerId,
        livechat_visitor_id: websiteVisitorId1,
    });
    const { openDiscuss } = await start({
        discuss: {
            context: {
                active_id: `mail.channel_${mailChannelId1}`,
            },
        },
    });
    await openDiscuss();
    assert.containsOnce(
        document.body,
        '.o_VisitorBanner',
        "should have a visitor banner",
    );
    assert.strictEqual(
        document.querySelector('.o_VisitorBanner_visitor').textContent,
        "Partner Visitor",
        "should have partner name as display name of logged visitor on the visitor banner"
    );
});

QUnit.test('livechat without visitor should not show visitor banner', async function (assert) {
    assert.expect(2);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({});
    const mailChannelId1 = pyEnv['mail.channel'].create({
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: resPartnerId1 }],
        ],
        channel_type: 'livechat',
        livechat_operator_id: pyEnv.currentPartnerId,
    });
    const { openDiscuss } = await start({
        discuss: {
            context: {
                active_id: `mail.channel_${mailChannelId1}`,
            },
        },
    });
    await openDiscuss();
    assert.containsOnce(
        document.body,
        '.o_MessageList',
        "should have a message list",
    );
    assert.containsNone(
        document.body,
        '.o_VisitorBanner',
        "should not have any visitor banner",
    );
});

QUnit.test('non-livechat channel should not show visitor banner', async function (assert) {
    assert.expect(2);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({ name: "General" });
    const { openDiscuss } = await start({
        discuss: {
            context: {
                active_id: `mail.channel_${mailChannelId1}`,
            },
        },
    });
    await openDiscuss();
    assert.containsOnce(
        document.body,
        '.o_MessageList',
        "should have a message list",
    );
    assert.containsNone(
        document.body,
        '.o_VisitorBanner',
        "should not have any visitor banner",
    );
});

});
});
