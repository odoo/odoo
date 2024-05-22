odoo.define('website_livechat/static/src/components/discuss/discuss_tests.js', function (require) {
'use strict';

const {
    afterEach,
    beforeEach,
    start,
} = require('mail/static/src/utils/test_utils.js');

QUnit.module('website_livechat', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('discuss', {}, function () {
QUnit.module('discuss_tests.js', {
    beforeEach() {
        beforeEach(this);

        this.start = async params => {
            const { env, widget } = await start(Object.assign({}, params, {
                autoOpenDiscuss: true,
                data: this.data,
                hasDiscuss: true,
            }));
            this.env = env;
            this.widget = widget;
        };
    },
    afterEach() {
        afterEach(this);
    },
});

QUnit.test('rendering of visitor banner', async function (assert) {
    assert.expect(13);

    this.data['res.country'].records.push({
        id: 11,
        code: 'FAKE',
    });
    this.data['website.visitor'].records.push({
        id: 11,
        country_id: 11,
        display_name: 'Visitor #11',
        history: 'Home → Contact',
        is_connected: true,
        lang: "English",
        website: "General website",
    });
    this.data['mail.channel'].records.push({
        channel_type: 'livechat',
        id: 11,
        livechat_operator_id: this.data.currentPartnerId,
        livechat_visitor_id: 11,
        members: [this.data.currentPartnerId, this.data.publicPartnerId],
    });
    await this.start({
        discuss: {
            context: {
                active_id: 'mail.channel_11',
            },
        },
    });
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

    this.data['res.country'].records.push({
        id: 11,
        code: 'FAKE',
    });
    this.data['website.visitor'].records.push({
        id: 11,
        country_id: 11,
        display_name: 'Visitor #11',
        history: 'Home → Contact',
        is_connected: true,
        lang: "English",
        website: "General website",
    });
    this.data['mail.channel'].records.push({
        channel_type: 'livechat',
        id: 11,
        livechat_operator_id: this.data.currentPartnerId,
        livechat_visitor_id: 11,
        members: [this.data.currentPartnerId, this.data.publicPartnerId],
    });
    await this.start({
        discuss: {
            context: {
                active_id: 'mail.channel_11',
            },
        },
    });
    assert.containsOnce(
        document.body,
        '.o_VisitorBanner',
        "should have a visitor banner",
    );
});

QUnit.test('livechat with logged visitor should show visitor banner', async function (assert) {
    assert.expect(2);

    this.data['res.country'].records.push({
        id: 11,
        code: 'FAKE',
    });
    this.data['res.partner'].records.push({
        id: 12,
        name: 'Partner Visitor',
    });
    this.data['website.visitor'].records.push({
        id: 11,
        country_id: 11,
        display_name: 'Visitor #11',
        history: 'Home → Contact',
        is_connected: true,
        lang: "English",
        partner_id: 12,
        website: "General website",
    });
    this.data['mail.channel'].records.push({
        channel_type: 'livechat',
        id: 11,
        livechat_operator_id: this.data.currentPartnerId,
        livechat_visitor_id: 11,
        members: [this.data.currentPartnerId, 12],
    });
    await this.start({
        discuss: {
            context: {
                active_id: 'mail.channel_11',
            },
        },
    });
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

    this.data['res.partner'].records.push({ id: 11 });
    this.data['mail.channel'].records.push({
        channel_type: 'livechat',
        id: 11,
        livechat_operator_id: this.data.currentPartnerId,
        members: [this.data.currentPartnerId, 11],
    });
    await this.start({
        discuss: {
            context: {
                active_id: 'mail.channel_11',
            },
        },
    });
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

    this.data['mail.channel'].records.push({ id: 11, name: "General" });
    await this.start({
        discuss: {
            context: {
                active_id: 'mail.channel_11',
            },
        },
    });
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
});

});
