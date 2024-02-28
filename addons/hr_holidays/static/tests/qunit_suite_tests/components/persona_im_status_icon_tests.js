/** @odoo-module **/

import { UPDATE_BUS_PRESENCE_DELAY } from '@bus/im_status_service';

import { start, startServer } from '@mail/../tests/helpers/test_utils';

QUnit.module('hr_holidays', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('persona_im_status_icon_tests.js');

QUnit.test('on leave & online', async function (assert) {
    assert.expect(2);

    const pyEnv = await startServer();
    const partnerId = pyEnv['res.partner'].create({ im_status: 'leave_online' });
    const mailChannelId = pyEnv['mail.channel'].create({});
    pyEnv['mail.message'].create({
        author_id: partnerId,
        body: 'not empty',
        model: 'mail.channel',
        res_id: mailChannelId,
    });
    const { advanceTime, afterNextRender, openDiscuss } = await start({
        discuss: {
            params: {
                default_active_id: mailChannelId,
            },
        },
        hasTimeControl: true,
    });
    await openDiscuss();
    await afterNextRender(() => advanceTime(UPDATE_BUS_PRESENCE_DELAY));
    assert.hasClass(
        document.querySelector('.o_PersonaImStatusIcon_icon'),
        'o-online',
        "persona IM status icon should have online status rendering"
    );
    assert.hasClass(
        document.querySelector('.o_PersonaImStatusIcon_icon'),
        'fa-plane',
        "persona IM status icon should have leave status rendering"
    );
});

QUnit.test('on leave & away', async function (assert) {
    assert.expect(2);

    const pyEnv = await startServer();
    const partnerId = pyEnv['res.partner'].create({ im_status: 'leave_away' });
    const mailChannelId = pyEnv['mail.channel'].create({});
    pyEnv['mail.message'].create({
        author_id: partnerId,
        body: 'not empty',
        model: 'mail.channel',
        res_id: mailChannelId,
    });
    const { advanceTime, afterNextRender, openDiscuss } = await start({
        discuss: {
            params: {
                default_active_id: mailChannelId,
            },
        },
        hasTimeControl: true,
    });
    await openDiscuss();
    await afterNextRender(() => advanceTime(UPDATE_BUS_PRESENCE_DELAY));
    assert.hasClass(
        document.querySelector('.o_PersonaImStatusIcon_icon'),
        'o-away',
        "persona IM status icon should have away status rendering"
    );
    assert.hasClass(
        document.querySelector('.o_PersonaImStatusIcon_icon'),
        'fa-plane',
        "persona IM status icon should have leave status rendering"
    );
});

QUnit.test('on leave & offline', async function (assert) {
    assert.expect(2);

    const pyEnv = await startServer();
    const partnerId = pyEnv['res.partner'].create({ im_status: 'leave_offline' });
    const mailChannelId = pyEnv['mail.channel'].create({});
    pyEnv['mail.message'].create({
        author_id: partnerId,
        body: 'not empty',
        model: 'mail.channel',
        res_id: mailChannelId,
    });
    const { advanceTime, afterNextRender, openDiscuss } = await start({
        discuss: {
            params: {
                default_active_id: mailChannelId,
            },
        },
        hasTimeControl: true,
    });
    await openDiscuss();
    await afterNextRender(() => advanceTime(UPDATE_BUS_PRESENCE_DELAY));
    assert.hasClass(
        document.querySelector('.o_PersonaImStatusIcon_icon'),
        'o-offline',
        "persona IM status icon should have offline status rendering"
    );
    assert.hasClass(
        document.querySelector('.o_PersonaImStatusIcon_icon'),
        'fa-plane',
        "persona IM status icon should have leave status rendering"
    );
});

});
});
