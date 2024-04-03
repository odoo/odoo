/** @odoo-module **/

import { makeDeferred } from '@mail/utils/deferred';
import { patchUiSize, SIZES } from '@mail/../tests/helpers/patch_ui_size';
import {
    afterNextRender,
    dragenterFiles,
    dropFiles,
    isScrolledToBottom,
    nextAnimationFrame,
    start,
    startServer,
} from '@mail/../tests/helpers/test_utils';

import fieldRegistry from 'web.field_registry';
import { dom, file, nextTick } from 'web.test_utils';
import { registerCleanup } from "@web/../tests/helpers/cleanup";

const { createFile } = file;

const { triggerEvent } = dom;

QUnit.module('mail', {}, function () {
QUnit.module('widgets', {}, function () {
QUnit.module('form_renderer_tests.js');

QUnit.test('[technical] spinner when messaging is not created', async function (assert) {
    /**
     * Creation of messaging in env is async due to generation of models being
     * async. Generation of models is async because it requires parsing of all
     * JS modules that contain pieces of model definitions.
     *
     * Time of having no messaging is very short, almost imperceptible by user
     * on UI, but the display should not crash during this critical time period.
     */
    assert.expect(3);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({
        display_name: "second partner",
    });
    const views = {
        'res.partner,false,form':
            `<form string="Partners">
                <sheet>
                    <field name="name"/>
                </sheet>
                <div class="oe_chatter"></div>
            </form>`,
    };
    const { openView } = await start({
        messagingBeforeCreationDeferred: makeDeferred(), // block messaging creation
        serverData: { views },
        waitUntilMessagingCondition: 'none',
    });
    await openView({
        res_model: 'res.partner',
        res_id: resPartnerId1,
        views: [[false, 'form']],
    });
    assert.containsOnce(
        document.body,
        '.o_ChatterContainer',
        "should display chatter container even when messaging is not created yet"
    );
    assert.containsOnce(
        document.body,
        '.o_ChatterContainer_noChatter',
        "chatter container should not display any chatter when messaging not created"
    );
    assert.strictEqual(
        document.querySelector('.o_ChatterContainer').textContent,
        "Please wait...",
        "chatter container should display spinner when messaging not yet created"
    );
});

QUnit.test('[technical] keep spinner on transition from messaging non-created to messaging created (and non-initialized)', async function (assert) {
    /**
     * Creation of messaging in env is async due to generation of models being
     * async. Generation of models is async because it requires parsing of all
     * JS modules that contain pieces of model definitions.
     *
     * Time of having no messaging is very short, almost imperceptible by user
     * on UI, but the display should not crash during this critical time period.
     */
    assert.expect(4);

    const pyEnv = await startServer();
    const messagingBeforeCreationDeferred = makeDeferred();
    const resPartnerId1 = pyEnv['res.partner'].create({
        display_name: "second partner",
    });
    const views = {
        'res.partner,false,form':
            `<form string="Partners">
                <sheet>
                    <field name="name"/>
                </sheet>
                <div class="oe_chatter"></div>
            </form>`,
    };
    const { openView } = await start({
        messagingBeforeCreationDeferred,
        async mockRPC(route, args) {
            if (route === '/mail/init_messaging') {
                await new Promise(() => {}); // simulate messaging never initialized
            }
        },
        serverData: { views },
        waitUntilMessagingCondition: 'none',
    });
    await openView({
        res_model: 'res.partner',
        res_id: resPartnerId1,
        views: [[false, 'form']],
    });
    assert.strictEqual(
        document.querySelector('.o_ChatterContainer').textContent,
        "Please wait...",
        "chatter container should display spinner when messaging not yet created"
    );
    assert.containsOnce(
        document.body,
        '.o_ChatterContainer_noChatter',
        "chatter container should not display any chatter when messaging not created"
    );

    // simulate messaging become created
    messagingBeforeCreationDeferred.resolve();
    await nextAnimationFrame();
    assert.strictEqual(
        document.querySelector('.o_ChatterContainer').textContent,
        "Please wait...",
        "chatter container should still display spinner when messaging is created but not initialized"
    );
    assert.containsOnce(
        document.body,
        '.o_ChatterContainer_noChatter',
        "chatter container should still not display any chatter when messaging not initialized"
    );
});

QUnit.test('spinner when messaging is created but not initialized', async function (assert) {
    assert.expect(3);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({
        display_name: "second partner",
    });
    const views = {
        'res.partner,false,form':
            `<form string="Partners">
                <sheet>
                    <field name="name"/>
                </sheet>
                <div class="oe_chatter"></div>
            </form>`,
    };
    const { openView } = await start({
        async mockRPC(route, args) {
            if (route === '/mail/init_messaging') {
                await new Promise(() => {}); // simulate messaging never initialized
            }
        },
        serverData: { views },
        waitUntilMessagingCondition: 'created',
    });
    await openView({
        res_model: 'res.partner',
        res_id: resPartnerId1,
        views: [[false, 'form']],
    });
    assert.containsOnce(
        document.body,
        '.o_ChatterContainer',
        "should display chatter container even when messaging is not fully initialized"
    );
    assert.containsOnce(
        document.body,
        '.o_ChatterContainer_noChatter',
        "chatter container should not display any chatter when messaging not initialized"
    );
    assert.strictEqual(
        document.querySelector('.o_ChatterContainer').textContent,
        "Please wait...",
        "chatter container should display spinner when messaging not yet initialized"
    );
});

QUnit.test('transition non-initialized messaging to initialized messaging: display spinner then chatter', async function (assert) {
    assert.expect(3);

    const pyEnv = await startServer();
    const messagingBeforeInitializationDeferred = makeDeferred();
    const resPartnerId1 = pyEnv['res.partner'].create({
        display_name: "second partner",
    });
    const views = {
        'res.partner,false,form':
            `<form string="Partners">
                <sheet>
                    <field name="name"/>
                </sheet>
                <div class="oe_chatter"></div>
            </form>`,
    };
    const { openView } = await start({
        async mockRPC(route, args) {
            if (route === '/mail/init_messaging') {
                await messagingBeforeInitializationDeferred;
            }
        },
        serverData: { views },
        waitUntilMessagingCondition: 'created',
    });
    await openView({
        res_model: 'res.partner',
        res_id: resPartnerId1,
        views: [[false, 'form']],
    });
    assert.strictEqual(
        document.querySelector('.o_ChatterContainer').textContent,
        "Please wait...",
        "chatter container should display spinner when messaging not yet initialized"
    );
    assert.containsOnce(
        document.body,
        '.o_ChatterContainer_noChatter',
        "chatter container should not display any chatter when messaging not initialized"
    );

    // Simulate messaging becomes initialized
    await afterNextRender(() => messagingBeforeInitializationDeferred.resolve());
    assert.containsNone(
        document.body,
        '.o_ChatterContainer_noChatter',
        "chatter container should now display chatter when messaging becomes initialized"
    );
});

QUnit.test('basic chatter rendering', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({ display_name: "second partner" });
    const views = {
        'res.partner,false,form':
            `<form string="Partners">
                <sheet>
                    <field name="name"/>
                </sheet>
                <div class="oe_chatter"></div>
            </form>`,
    };
    const { openView } = await start({
        serverData: { views },
    });
    await openView({
        res_model: 'res.partner',
        res_id: resPartnerId1,
        views: [[false, 'form']],
    });
    assert.strictEqual(
        document.querySelectorAll(`.o_Chatter`).length,
        1,
        "there should be a chatter"
    );
});

QUnit.test('basic chatter rendering without followers', async function (assert) {
    assert.expect(6);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({ display_name: "second partner" });
    const views = {
        'res.partner,false,form':
            `<form string="Partners">
                <sheet>
                    <field name="name"/>
                </sheet>
                <div class="oe_chatter">
                    <field name="activity_ids"/>
                    <field name="message_ids"/>
                </div>
            </form>`,
    };
    const { openView } = await start({
        serverData: { views },
    });
    await openView({
        res_model: 'res.partner',
        res_id: resPartnerId1,
        views: [[false, 'form']],
    });
    assert.containsOnce(
        document.body,
        '.o_Chatter',
        "there should be a chatter"
    );
    assert.containsOnce(
        document.body,
        '.o_ChatterTopbar',
        "there should be a chatter topbar"
    );
    assert.containsOnce(
        document.body,
        '.o_ChatterTopbar_buttonAddAttachments',
        "there should be an attachment button"
    );
    assert.containsOnce(
        document.body,
        '.o_ChatterTopbar_buttonScheduleActivity',
        "there should be a schedule activity button"
    );
    assert.containsNone(
        document.body,
        '.o_FollowerListMenu',
        "there should be no followers menu because the 'message_follower_ids' field is not present in 'oe_chatter'"
    );
    assert.containsOnce(
        document.body,
        '.o_Chatter_thread',
        "there should be a thread"
    );
});

QUnit.test('basic chatter rendering without activities', async function (assert) {
    assert.expect(6);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({ display_name: "second partner" });
    const views = {
        'res.partner,false,form':
            `<form string="Partners">
                <sheet>
                    <field name="name"/>
                </sheet>
                <div class="oe_chatter">
                    <field name="message_follower_ids"/>
                    <field name="message_ids"/>
                </div>
            </form>`,
    };
    const { openView } = await start({
        serverData: { views },
    });
    await openView({
        res_model: 'res.partner',
        res_id: resPartnerId1,
        views: [[false, 'form']],
    });
    assert.containsOnce(
        document.body,
        '.o_Chatter',
        "there should be a chatter"
    );
    assert.containsOnce(
        document.body,
        '.o_ChatterTopbar',
        "there should be a chatter topbar"
    );
    assert.containsOnce(
        document.body,
        '.o_ChatterTopbar_buttonAddAttachments',
        "there should be an attachment button"
    );
    assert.containsNone(
        document.body,
        '.o_ChatterTopbar_buttonScheduleActivity',
        "there should be no schedule activity button because the 'activity_ids' field is not present in 'oe_chatter'"
    );
    assert.containsOnce(
        document.body,
        '.o_FollowerListMenu',
        "there should be a followers menu"
    );
    assert.containsOnce(
        document.body,
        '.o_Chatter_thread',
        "there should be a thread"
    );
});

QUnit.test('basic chatter rendering without messages', async function (assert) {
    assert.expect(6);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({ display_name: "second partner" });
    const views = {
        'res.partner,false,form':
            `<form string="Partners">
                <sheet>
                    <field name="name"/>
                </sheet>
                <div class="oe_chatter">
                    <field name="message_follower_ids"/>
                    <field name="activity_ids"/>
                </div>
            </form>`,
    };
    const { openView } = await start({
        serverData: { views },
    });
    await openView({
        res_model: 'res.partner',
        res_id: resPartnerId1,
        views: [[false, 'form']],
    });
    assert.containsOnce(
        document.body,
        '.o_Chatter',
        "there should be a chatter"
    );
    assert.containsOnce(
        document.body,
        '.o_ChatterTopbar',
        "there should be a chatter topbar"
    );
    assert.containsOnce(
        document.body,
        '.o_ChatterTopbar_buttonAddAttachments',
        "there should be an attachment button"
    );
    assert.containsOnce(
        document.body,
        '.o_ChatterTopbar_buttonScheduleActivity',
        "there should be a schedule activity button"
    );
    assert.containsOnce(
        document.body,
        '.o_FollowerListMenu',
        "there should be a followers menu"
    );
    assert.containsNone(
        document.body,
        '.o_Chatter_thread',
        "there should be no thread because the 'message_ids' field is not present in 'oe_chatter'"
    );
});

QUnit.test('chatter updating', async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const [resPartnerId1, resPartnerId2] = pyEnv['res.partner'].create([
        { display_name: "first partner" },
        { display_name: "second partner" },
    ]);
    pyEnv['mail.message'].create({ body: "not empty", model: 'res.partner', res_id: resPartnerId2 });
    const views = {
        'res.partner,false,form':
            `<form string="Partners">
                <sheet>
                    <field name="name"/>
                </sheet>
                <div class="oe_chatter">
                    <field name="message_ids"/>
                </div>
            </form>`,
    };
    const { afterEvent, openFormView } = await start({
        serverData: { views },
    });
    await openFormView(
        {
            res_model: 'res.partner',
            res_id: resPartnerId1,
        },
        {
            props: {
                resIds: [resPartnerId1, resPartnerId2],
            },
        }
    );
    await afterNextRender(() => afterEvent({
        eventName: 'o-thread-view-hint-processed',
        func: () => document.querySelector('.o_pager_next').click(),
        message: "should wait until partner 12 thread loaded messages after clicking on next",
        predicate: ({ hint, threadViewer }) => {
            return (
                hint.type === 'messages-loaded' &&
                threadViewer.thread.model === 'res.partner' &&
                threadViewer.thread.id === resPartnerId2
            );
        },
    }));
    assert.containsOnce(
        document.body,
        '.o_Message',
        "there should be a message in partner 12 thread"
    );
});

QUnit.test('post message on draft record', async function (assert) {
    const views = {
        'res.partner,false,form':
            `<form string="Partners">
                <sheet>
                    <field name="name"/>
                </sheet>
                <div class="oe_chatter">
                    <field name="message_ids"/>
                </div>
            </form>`,
    };
    const { click, insertText, openView } = await start({
        serverData: { views },
    });
    await openView({
        res_model: 'res.partner',
        views: [[false, 'form']],
    });
    await click('.o_ChatterTopbar_buttonSendMessage');
    await insertText('.o_ComposerTextInput_textarea', "Test");
    await click('.o_Composer_buttonSend');
    assert.containsOnce(document.body, ".o_Message");
    assert.strictEqual(
        document.querySelector(".o_Message_prettyBody").textContent,
        "Test",
    );
});

QUnit.test('schedule activities on draft record should prompt with scheduling an activity (proceed with action)', async function (assert) {
    const views = {
        'res.partner,false,form':
            `<form string="Partners">
                <sheet>
                    <field name="name"/>
                </sheet>
                <div class="oe_chatter">
                    <field name="activity_ids"/>
                </div>
            </form>`,
    };
    const { click, openView } = await start({ serverData: { views } });
    await openView({ res_model: 'res.partner', views: [[false, 'form']] });
    await click('.o_ChatterTopbar_buttonScheduleActivity');
    assert.containsOnce(document.body, ".o_dialog:contains(Schedule Activity)")
});

QUnit.test('upload attachment on draft record', async function (assert) {
    const views = {
        'res.partner,false,form':
            `<form string="Partners">
                <sheet>
                    <field name="name"/>
                </sheet>
                <div class="oe_chatter">
                    <field name="message_ids"/>
                </div>
            </form>`,
    };
    const { openView } = await start({ serverData: { views }});
    await openView({
        res_model: 'res.partner',
        views: [[false, 'form']],
    });
    const file = await createFile({
        content: 'hello, world',
        contentType: 'text/plain',
        name: 'text.txt',
    });
    assert.containsNone(document.body, ".o_ChatterTopbar_buttonToggleAttachments:contains(1)");
    await afterNextRender(() => dragenterFiles(document.querySelector('.o_Chatter')));
    await afterNextRender(() => dropFiles(document.querySelector('.o_Chatter_dropZone'), [file]));
    assert.containsOnce(document.body, ".o_ChatterTopbar_buttonToggleAttachments:contains(1)");
});

QUnit.test('read more/less links are not duplicated when switching from read to edit mode', async function (assert) {
    assert.expect(3);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({});
    const mailMessageId1 = pyEnv['mail.message'].create({
        author_id: resPartnerId1,
        // "data-o-mail-quote" added by server is intended to be compacted in read more/less blocks
        body: `
            <div>
                Dear Joel Willis,<br>
                Thank you for your enquiry.<br>
                If you have any questions, please let us know.
                <br><br>
                Thank you,<br>
                <span data-o-mail-quote="1">-- <br data-o-mail-quote="1">
                    System
                </span>
            </div>
        `,
        model: 'res.partner',
        res_id: resPartnerId1,
    });
    const views = {
        'res.partner,false,form':
            `<form string="Partners">
                <sheet>
                    <field name="name"/>
                </sheet>
                <div class="oe_chatter">
                    <field name="message_ids"/>
                </div>
            </form>`,
    };
    const { afterEvent, openView } = await start({
        serverData: { views },
    });
    const openViewAction = {
        res_model: 'res.partner',
        res_id: resPartnerId1,
        views: [[false, 'form']],
    };
    await afterEvent({
        func: () => openView(openViewAction),
        eventName: 'o-component-message-read-more-less-inserted',
        message: "should wait until read more/less is inserted initially",
        predicate: ({ message }) => message.id === mailMessageId1,
    });
    assert.containsOnce(
        document.body,
        '.o_Chatter',
        "there should be a chatter"
    );
    assert.containsOnce(
        document.body,
        '.o_Message',
        "there should be a message"
    );
    assert.containsOnce(
        document.body,
        '.o_Message_readMoreLess',
        "there should be only one read more"
    );
});

QUnit.test('read more links becomes read less after being clicked', async function (assert) {
    assert.expect(5);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({});
    const mailMessageId1 = pyEnv['mail.message'].create([{
        author_id: resPartnerId1,
        // "data-o-mail-quote" added by server is intended to be compacted in read more/less blocks
        body: `
            <div>
                Dear Joel Willis,<br>
                Thank you for your enquiry.<br>
                If you have any questions, please let us know.
                <br><br>
                Thank you,<br>
                <span data-o-mail-quote="1">-- <br data-o-mail-quote="1">
                    System
                </span>
            </div>
        `,
        model: 'res.partner',
        res_id: resPartnerId1,
    }]);
    const views = {
        'res.partner,false,form':
            `<form string="Partners">
                <sheet>
                    <field name="name"/>
                </sheet>
                <div class="oe_chatter">
                    <field name="message_ids"/>
                </div>
            </form>`,
    };
    const { afterEvent, openView } = await start({
        serverData: { views },
    });
    const openViewAction = {
        res_model: 'res.partner',
        res_id: resPartnerId1,
        views: [[false, 'form']],
    };
    await afterEvent({
        func: () => openView(openViewAction),
        eventName: 'o-component-message-read-more-less-inserted',
        message: "should wait until read more/less is inserted initially",
        predicate: ({ message }) => message.id === mailMessageId1,
    });
    assert.containsOnce(
        document.body,
        '.o_Chatter',
        "there should be a chatter"
    );
    assert.containsOnce(
        document.body,
        '.o_Message',
        "there should be a message"
    );
    assert.containsOnce(
        document.body,
        '.o_Message_readMoreLess',
        "there should be a read more"
    );
    assert.strictEqual(
        document.querySelector('.o_Message_readMoreLess').textContent,
        'Read More',
        "Read More/Less link should contain 'Read More' as text"
    );

    document.querySelector('.o_Message_readMoreLess').click();
    assert.strictEqual(
        document.querySelector('.o_Message_readMoreLess').textContent,
        'Read Less',
        "Read Less/Less link should contain 'Read Less' as text after it has been clicked"
    );
});

QUnit.test('Form view not scrolled when switching record', async function (assert) {
    assert.expect(6);

    const pyEnv = await startServer();
    const [resPartnerId1, resPartnerId2] = pyEnv['res.partner'].create([
        {
            description: [...Array(60).keys()].join('\n'),
            display_name: "Partner 1",
        },
        {
            display_name: "Partner 2",
        },
    ]);

    const messages = [...Array(60).keys()].map(id => {
        return {
            model: 'res.partner',
            res_id: id % 2 ? resPartnerId1 : resPartnerId2,
        };
    });
    pyEnv['mail.message'].create(messages);
    const views = {
        'res.partner,false,form':
            `<form string="Partners">
                <sheet>
                    <field name="name"/>
                    <field name="description"/>
                </sheet>
                <div class="oe_chatter">
                    <field name="message_ids"/>
                </div>
            </form>`,
    };
    patchUiSize({ size: SIZES.LG });
    const { click, openView } = await start({
        serverData: { views },
    });
    await openView(
        {
            res_model: 'res.partner',
            res_id: resPartnerId1,
            views: [[false, 'form']],
        },
        {
            resIds: [resPartnerId1, resPartnerId2],
        }
    );

    const controllerContentEl = document.querySelector('.o_content');

    assert.strictEqual(
        document.querySelector('.breadcrumb-item.active').textContent,
        'Partner 1',
        "Form view should display partner 'Partner 1'"
    );
    assert.strictEqual(controllerContentEl.scrollTop, 0,
        "The top of the form view is visible"
    );

    await afterNextRender(async () => {
        controllerContentEl.scrollTop = controllerContentEl.scrollHeight - controllerContentEl.clientHeight;
        await triggerEvent(
            document.querySelector('.o_ThreadView_messageList'),
            'scroll'
        );
    });
    assert.ok(
        isScrolledToBottom(controllerContentEl),
        "The controller container should be scrolled to its bottom"
    );

    await click('.o_pager_next');
    assert.strictEqual(
        document.querySelector('.breadcrumb-item.active').textContent,
        'Partner 2',
        "The form view should display partner 'Partner 2'"
    );
    assert.strictEqual(controllerContentEl.scrollTop, 0,
        "The top of the form view should be visible when switching record from pager"
    );

    await click('.o_pager_previous');
    assert.strictEqual(controllerContentEl.scrollTop, 0,
        "Form view's scroll position should have been reset when switching back to first record"
    );
});

QUnit.test('Attachments that have been unlinked from server should be visually unlinked from record', async function (assert) {
    // Attachments that have been fetched from a record at certain time and then
    // removed from the server should be reflected on the UI when the current
    // partner accesses this record again.
    assert.expect(2);

    const pyEnv = await startServer();
    const [resPartnerId1, resPartnerId2] = pyEnv['res.partner'].create([
        { display_name: "Partner1" },
        { display_name: "Partner2" },
    ]);
    const [irAttachmentId1] = pyEnv['ir.attachment'].create([
        {
            mimetype: 'text.txt',
            res_id: resPartnerId1,
            res_model: 'res.partner',
        },
        {
            mimetype: 'text.txt',
            res_id: resPartnerId1,
            res_model: 'res.partner',
        },
    ]);
    const views = {
        'res.partner,false,form':
            `<form string="Partners">
                <sheet>
                    <field name="name"/>
                </sheet>
                <div class="oe_chatter">
                    <field name="message_ids"/>
                </div>
            </form>`,
    };
    const { click, openView } = await start({
        serverData: { views },
    });
    await openView(
        {
            res_model: 'res.partner',
            res_id: resPartnerId1,
            views: [[false, 'form']],
        },
        {
            resId: resPartnerId1,
            resIds: [resPartnerId1, resPartnerId2],
        },
    );
    assert.strictEqual(
        document.querySelector('.o_ChatterTopbar_buttonCount').textContent,
        '2',
        "Partner1 should have 2 attachments initially"
    );

    // The attachment links are updated on (re)load,
    // so using pager is a way to reload the record "Partner1".
    await click('.o_pager_next');
    // Simulate unlinking attachment 1 from Partner 1.
    pyEnv['ir.attachment'].write([irAttachmentId1], { res_id: 0 });
    await click('.o_pager_previous');
    assert.strictEqual(
        document.querySelector('.o_ChatterTopbar_buttonCount').textContent,
        '1',
        "Partner1 should now have 1 attachment after it has been unlinked from server"
    );
});

QUnit.test('chatter just contains "creating a new record" message during the creation of a new record after having displayed a chatter for an existing record', async function (assert) {
    assert.expect(2);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({});
    const views = {
        'res.partner,false,form':
            `<form string="Partners">
                <sheet>
                    <field name="name"/>
                </sheet>
                <div class="oe_chatter">
                    <field name="message_ids"/>
                </div>
            </form>`,
    };
    const { click, openView } = await start({
        serverData: { views },
    });
    await openView({
        res_model: 'res.partner',
        res_id: resPartnerId1,
        views: [[false, 'form']],
    });

    await click('.o_form_button_create');
    assert.containsOnce(
        document.body,
        '.o_Message',
        "Should have a single message when creating a new record"
    );
    assert.strictEqual(
        document.querySelector('.o_Message_content').textContent,
        'Creating a new record...',
        "the message content should be in accord to the creation of this record"
    );
});

QUnit.test('[TECHNICAL] unfolded read more/less links should not fold on message click besides those button links', async function (assert) {
    // message click triggers a re-render. Before writing of this test, the
    // insertion of read more/less links were done during render. This meant
    // any re-render would re-insert the read more/less links. If some button
    // links were unfolded, any re-render would fold them again.
    //
    // This previous behavior is undesirable, and results to bothersome UX
    // such as inability to copy/paste unfolded message content due to click
    // from text selection automatically folding all read more/less links.
    assert.expect(3);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({ display_name: "Someone" });
    pyEnv['mail.message'].create({
        author_id: resPartnerId1,
        // "data-o-mail-quote" added by server is intended to be compacted in read more/less blocks
        body: `
            <div>
                Dear Joel Willis,<br>
                Thank you for your enquiry.<br>
                If you have any questions, please let us know.
                <br><br>
                Thank you,<br>
                <span data-o-mail-quote="1">-- <br data-o-mail-quote="1">
                    System
                </span>
            </div>
        `,
        model: 'res.partner',
        res_id: resPartnerId1,
    });
    const views = {
        'res.partner,false,form':
            `<form string="Partners">
                <sheet>
                    <field name="name"/>
                </sheet>
                <div class="oe_chatter">
                    <field name="message_ids"/>
                </div>
            </form>`,
    };
    const { click, openView } = await start({
        serverData: { views },
    });
    await openView({
        res_model: 'res.partner',
        res_id: resPartnerId1,
        views: [[false, 'form']],
    });
    assert.strictEqual(
        document.querySelector('.o_Message_readMoreLess').textContent,
        "Read More",
        "Read More/Less link on message should be folded initially (Read More)"
    );

    document.querySelector('.o_Message_readMoreLess').click(),
    assert.strictEqual(
        document.querySelector('.o_Message_readMoreLess').textContent,
        "Read Less",
        "Read More/Less link on message should be unfolded after a click from initial rendering (read less)"
    );

    await click('.o_Message');
    assert.strictEqual(
        document.querySelector('.o_Message_readMoreLess').textContent,
        "Read Less",
        "Read More/Less link on message should still be unfolded after a click on message aside of this button click (Read Less)"
    );
});

QUnit.test('chatter does not flicker when the form view is re-rendered', async function (assert) {
    const pyEnv = await startServer();
    const [resPartnerId1, resPartnerId2] = pyEnv['res.partner'].create([
        { display_name: "first partner" },
        { display_name: "second partner" },
    ]);

    // define an asynchronous field and use it in the form to ease testing
    let def;
    const FieldChar = fieldRegistry.get("char");
    const AsyncWidget = FieldChar.extend({
        willStart() {
            return Promise.resolve(def);
        },
    });
    fieldRegistry.add("async_widget", AsyncWidget);
    registerCleanup(() => {
        delete fieldRegistry.map.async_widget;
    });

    const views = {
        'res.partner,false,form':
            `<form string="Partners">
                <sheet>
                    <field name="name"/>
                </sheet>
                <div class="oe_chatter"></div>
            </form>`,
    };
    const { openView } = await start({
        serverData: { views },
    });
    await openView({
        res_model: 'res.partner',
        res_id: resPartnerId1,
        views: [[false, 'form']],
    }, { resIds: [resPartnerId1, resPartnerId2]});
    assert.strictEqual(
        document.querySelectorAll(`.o_Chatter`).length,
        1,
        "there should be a chatter"
    );
    def = makeDeferred();
    document.querySelector('.o_pager_next').click();
    await nextTick();

    assert.strictEqual(
        document.querySelectorAll(`.o_Chatter`).length,
        1,
        "there should be a chatter"
    );
    def.resolve();
    await nextTick();

    assert.strictEqual(
        document.querySelectorAll(`.o_Chatter`).length,
        1,
        "there should be a chatter"
    );
});

});
});
