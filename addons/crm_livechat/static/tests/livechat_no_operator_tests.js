odoo.define('crm_livechat.livechatNoOperatorTest', function (require) {
"use strict";

const ajax = require('web.ajax');
const core = require('web.core');
const concurrency = require('web.concurrency');
const LivechatButton = require('im_livechat.im_livechat').LivechatButton;
const mailTestUtils = require('mail.testUtils');
const session = require('web.session');
const testUtils = require('web.test_utils');
const Widget = require('web.Widget');


QUnit.module('crm_livechat', {
    before: function () {
        this.services = mailTestUtils.getMailServices();
        return ajax.loadXML('/crm_livechat/static/src/xml/im_livechat.xml', core.qweb);
}}, function () {

QUnit.test('livechat: generate a lead while operator not replying', async function (assert) {
    assert.expect(4);

    const parent = new Widget();
    const options = {
        channel_id: 1,
        channel_name: "YourWebsite.com",
        generate_lead: true,
    };

    const livechatButton = new LivechatButton(parent, location.origin, options);

    const livechatdata = {
        operator_pid: [false, "YourCompany, Mitchell Admin"],
        uuid: "c038331c-f32d-448a-9be3-012e5b826381",
    };

    testUtils.mock.patch(session, {
        rpc: function (route, args) {
            if (route === '/im_livechat/init') {
                return Promise.resolve({available_for_me: true, rule: {}});
            } else if (route === '/im_livechat/get_session') {
                return Promise.resolve(livechatdata);
            } else if (route === '/mail/chat_post') {
                return Promise.resolve({});
            }
            return this._super.apply(this, arguments);
        }
    });

    testUtils.mock.addMockEnvironment(livechatButton, {
        services: this.services,
        mockRPC: function (route, args) {
            if (route === location.origin + '/livechat/generate_lead') {
                assert.strictEqual(args.channel_uuid, livechatdata.uuid, 'channel should be same');
                return Promise.resolve();
            }
            return this._super.apply(this, arguments);
        }
    });

    livechatButton._LeadGenerationTimer._duration = 2000;
    await livechatButton.appendTo($('#qunit-fixture'));

    // click on the livechat button to open the chat window
    await testUtils.dom.click(livechatButton.$el);
    const chatWindow = livechatButton._chatWindow;
    chatWindow.$input.val('hi');
    // post a message
    chatWindow.$input.trigger($.Event('keydown', {which: $.ui.keyCode.ENTER}));
    await concurrency.delay(livechatButton._LeadGenerationTimer._duration);

    assert.notOk(chatWindow.$('.o_thread_composer').is(':visible'), 'input box should be invisible');
    const leadForm = chatWindow.$('.o_lead_creation_form');
    assert.ok(leadForm.length, 'lead generation form should be visible');

    await testUtils.fields.editInput(leadForm.find('input[name="name"]'), 'test');
    await testUtils.fields.editInput(leadForm.find('input[name="email_from"]'), 'test@odoo.com');

    await testUtils.dom.click(leadForm.find('button'));

    assert.notOk(leadForm.is(':visible'), 'lead generation form should be invisible');

    testUtils.mock.unpatch(session);
    parent.destroy();
    livechatButton.destroy();
});

});
});
