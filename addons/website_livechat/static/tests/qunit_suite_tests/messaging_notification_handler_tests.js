/** @odoo-module **/

import {
    afterNextRender,
    start,
    startServer,
} from '@mail/../tests/helpers/test_utils';

import FormView from 'web.FormView';
import { mock } from 'web.test_utils';

QUnit.module('website_livechat', {}, function () {
QUnit.module('messaging_notification_handler_tests.js');

QUnit.test('should open chat window on send chat request to website visitor', async function (assert) {
    assert.expect(3);

    const pyEnv = await startServer();
    const websiteVisitorId1 = pyEnv['website.visitor'].create({
        display_name: "Visitor #11",
    });
    const { env, widget } = await start({
        hasView: true,
        // View params
        View: FormView,
        model: 'website.visitor',
        arch: `
            <form>
                <header>
                    <button name="action_send_chat_request" string="Send chat request" class="btn btn-primary" type="button"/>
                </header>
                <field name="name"/>
            </form>
        `,
        res_id: websiteVisitorId1,
    });
    mock.intercept(widget, 'execute_action', payload => {
        env.services.rpc({
            route: '/web/dataset/call_button',
            params: {
                args: [payload.data.env.resIDs],
                kwargs: { context: payload.data.env.context },
                method: payload.data.action_data.name,
                model: payload.data.env.model,
            }
        });
    });

    await afterNextRender(() =>
        document.querySelector('button[name="action_send_chat_request"]').click()
    );
    assert.containsOnce(
        document.body,
        '.o_ChatWindow',
        "should have a chat window open after sending chat request to website visitor"
    );
    assert.hasClass(
        document.querySelector('.o_ChatWindow'),
        'o-focused',
        "chat window of livechat should be focused on open"
    );
    assert.strictEqual(
        document.querySelector('.o_ChatWindowHeader_name').textContent,
        "Visitor #11",
        "chat window of livechat should have name of visitor in the name"
    );
});

});
