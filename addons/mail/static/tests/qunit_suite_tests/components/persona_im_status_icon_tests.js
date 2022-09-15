/** @odoo-module **/

import { UPDATE_BUS_PRESENCE_DELAY } from '@bus/im_status_service';

import { start, startServer } from '@mail/../tests/helpers/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('persona_im_status_icon_tests.js');

QUnit.test('initially online', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const partnerId = pyEnv['res.partner'].create({ im_status: 'online' });
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
    assert.strictEqual(
        document.querySelectorAll(`.o_PersonaImStatusIcon.o-online`).length,
        1,
        "persona IM status icon should have online status rendering"
    );
});

QUnit.test('initially offline', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const partnerId = pyEnv['res.partner'].create({ im_status: 'offline' });
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
    assert.strictEqual(
        document.querySelectorAll(`.o_PersonaImStatusIcon.o-offline`).length,
        1,
        "persona IM status icon should have offline status rendering"
    );
});

QUnit.test('initially away', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const partnerId = pyEnv['res.partner'].create({ im_status: 'away' });
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
    assert.strictEqual(
        document.querySelectorAll(`.o_PersonaImStatusIcon.o-away`).length,
        1,
        "persona IM status icon should have away status rendering"
    );
});

QUnit.test('change icon on change partner im_status', async function (assert) {
    assert.expect(4);

    const pyEnv = await startServer();
    const partnerId = pyEnv['res.partner'].create({ im_status: 'online' });
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
    assert.strictEqual(
        document.querySelectorAll(`.o_PersonaImStatusIcon.o-online`).length,
        1,
        "persona IM status icon should have online status rendering"
    );

    pyEnv['res.partner'].write([partnerId], { im_status: 'offline' });
    await afterNextRender(() => advanceTime(UPDATE_BUS_PRESENCE_DELAY));
    assert.strictEqual(
        document.querySelectorAll(`.o_PersonaImStatusIcon.o-offline`).length,
        1,
        "persona IM status icon should have offline status rendering"
    );

    pyEnv['res.partner'].write([partnerId], { im_status: 'away' });
    await afterNextRender(() => advanceTime(UPDATE_BUS_PRESENCE_DELAY));
    assert.strictEqual(
        document.querySelectorAll(`.o_PersonaImStatusIcon.o-away`).length,
        1,
        "persona IM status icon should have away status rendering"
    );

    pyEnv['res.partner'].write([partnerId], { im_status: 'online' });
    await afterNextRender(() => advanceTime(UPDATE_BUS_PRESENCE_DELAY));
    assert.strictEqual(
        document.querySelectorAll(`.o_PersonaImStatusIcon.o-online`).length,
        1,
        "persona IM status icon should have online status rendering in the end"
    );
});

});
});
