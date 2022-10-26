/** @odoo-module **/

import {
    start,
    startServer,
} from '@mail/../tests/helpers/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('call_main_view_tests.js');

QUnit.test('Join a call', async function (assert) {
    assert.expect(4);

    const pyEnv = await startServer();
    const mailChannelId = pyEnv['mail.channel'].create({});
    const { click, openDiscuss } = await start({
        discuss: {
            params: {
                default_active_id: `mail.channel_${mailChannelId}`,
            },
        },
    });
    await openDiscuss();
    await click('.o_ThreadViewTopbar_callButton');

    assert.containsOnce(
        document.body,
        '.o_CallView',
        "Should have a call view"
    );
    assert.containsOnce(
        document.body,
        '.o_CallParticipantCard',
        "Should have a call participant card"
    );
    assert.containsOnce(
        document.body,
        '.o_CallMainView_controls',
        "Should have call controls"
    );
    assert.containsNone(
        document.body,
        '.o_ThreadViewTopbar_callButton',
        "Should not have a join call button anymore"
    );
});

QUnit.test('Leave a call', async function (assert) {
    assert.expect(2);

    const pyEnv = await startServer();
    const mailChannelId = pyEnv['mail.channel'].create({});
    const { click, openDiscuss } = await start({
        discuss: {
            params: {
                default_active_id: `mail.channel_${mailChannelId}`,
            },
        },
    });
    await openDiscuss();
    await click('.o_ThreadViewTopbar_callButton');
    assert.containsOnce(
        document.body,
        '.o_CallActionList_callToggle',
        "Should have a button to leave the call"
    );
    await click('.o_CallActionList_callToggle');
    assert.containsNone(
        document.body,
        '.o_CallView',
        "Should not have a call view"
    );
});

});
});
