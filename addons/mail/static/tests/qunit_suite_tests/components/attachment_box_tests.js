/** @odoo-module **/

import { nextAnimationFrame, start, startServer } from '@mail/../tests/helpers/test_utils';
import { patchUiSize, SIZES } from '@mail/../tests/helpers/patch_ui_size';

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('attachment_box_tests.js');

QUnit.test('base empty rendering', async function (assert) {
    assert.expect(4);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({});
    const views = {
        'res.partner,false,form':
            `<form>
                <div class="oe_chatter">
                    <field name="message_ids"  options="{'open_attachments': True}"/>
                </div>
            </form>`,
    };
    const { messaging, openView } = await start({ serverData: { views } });
    await openView({
        res_id: resPartnerId1,
        res_model: 'res.partner',
        views: [[false, 'form']],
    });
    assert.strictEqual(
        document.querySelectorAll(`.o_AttachmentBox`).length,
        1,
        "should have an attachment box"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_AttachmentBox_buttonAdd`).length,
        1,
        "should have a button add"
    );
    assert.ok(
        messaging.models['Chatter'].all()[0].attachmentBoxView.fileUploader,
        "should have a file uploader"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_AttachmentBox .o_AttachmentCard`).length,
        0,
        "should not have any attachment"
    );
});

QUnit.test('base non-empty rendering', async function (assert) {
    assert.expect(4);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({});
    pyEnv['ir.attachment'].create([
        {
            mimetype: 'text/plain',
            name: 'Blah.txt',
            res_id: resPartnerId1,
            res_model: 'res.partner',
        },
        {
            mimetype: 'text/plain',
            name: 'Blu.txt',
            res_id: resPartnerId1,
            res_model: 'res.partner',
        },
    ]);
    const views = {
        'res.partner,false,form':
            `<form>
                <div class="oe_chatter">
                    <field name="message_ids"  options="{'open_attachments': True}"/>
                </div>
            </form>`,
    };
    const { messaging, openView } = await start({ serverData: { views } });
    await openView({
        res_id: resPartnerId1,
        res_model: 'res.partner',
        views: [[false, 'form']],
    });
    assert.strictEqual(
        document.querySelectorAll(`.o_AttachmentBox`).length,
        1,
        "should have an attachment box"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_AttachmentBox_buttonAdd`).length,
        1,
        "should have a button add"
    );
    assert.ok(
        messaging.models['Chatter'].all()[0].attachmentBoxView.fileUploader,
        "should have a file uploader"
    );
    assert.strictEqual(
        document.querySelectorAll(`.o_attachmentBox_attachmentList`).length,
        1,
        "should have an attachment list"
    );
});

QUnit.test('view attachments', async function (assert) {
    assert.expect(7);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({});
    const [irAttachmentId1] = pyEnv['ir.attachment'].create([
        {
            mimetype: 'text/plain',
            name: 'Blah.txt',
            res_id: resPartnerId1,
            res_model: 'res.partner',
        },
        {
            mimetype: 'text/plain',
            name: 'Blu.txt',
            res_id: resPartnerId1,
            res_model: 'res.partner',
        },
    ]);
    const views = {
        'res.partner,false,form':
            `<form>
                <div class="oe_chatter">
                    <field name="message_ids"  options="{'open_attachments': True}"/>
                </div>
            </form>`,
    };
    const { click, messaging, openView } = await start({ serverData: { views } });
    await openView({
        res_id: resPartnerId1,
        res_model: 'res.partner',
        views: [[false, 'form']],
    });
    const firstAttachment = messaging.models['Attachment'].findFromIdentifyingData({ id: irAttachmentId1 });

    await click(`
        .o_AttachmentCard[data-id="${firstAttachment.localId}"]
        .o_AttachmentCard_image
    `);
    assert.containsOnce(
        document.body,
        '.o_Dialog',
        "a dialog should have been opened once attachment image is clicked",
    );
    assert.containsOnce(
        document.body,
        '.o_AttachmentViewer',
        "an attachment viewer should have been opened once attachment image is clicked",
    );
    assert.strictEqual(
        document.querySelector('.o_AttachmentViewer_name').textContent,
        'Blah.txt',
        "attachment viewer iframe should point to clicked attachment",
    );
    assert.containsOnce(
        document.body,
        '.o_AttachmentViewer_buttonNavigationNext',
        "attachment viewer should allow to see next attachment",
    );

    await click('.o_AttachmentViewer_buttonNavigationNext');
    assert.strictEqual(
        document.querySelector('.o_AttachmentViewer_name').textContent,
        'Blu.txt',
        "attachment viewer iframe should point to next attachment of attachment box",
    );
    assert.containsOnce(
        document.body,
        '.o_AttachmentViewer_buttonNavigationNext',
        "attachment viewer should allow to see next attachment",
    );

    await click('.o_AttachmentViewer_buttonNavigationNext');
    assert.strictEqual(
        document.querySelector('.o_AttachmentViewer_name').textContent,
        'Blah.txt',
        "attachment viewer iframe should point anew to first attachment",
    );
});

QUnit.test('remove attachment should ask for confirmation', async function (assert) {
    assert.expect(5);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({});
    pyEnv['ir.attachment'].create({
        mimetype: 'text/plain',
        name: 'Blah.txt',
        res_id: resPartnerId1,
        res_model: 'res.partner',
    });
    const views = {
        'res.partner,false,form':
            `<form>
                <div class="oe_chatter">
                    <field name="message_ids"  options="{'open_attachments': True}"/>
                </div>
            </form>`,
    };
    const { click, openView } = await start({ serverData: { views } });
    await openView({
        res_id: resPartnerId1,
        res_model: 'res.partner',
        views: [[false, 'form']],
    });
    assert.containsOnce(
        document.body,
        '.o_AttachmentCard',
        "should have an attachment",
    );
    assert.containsOnce(
        document.body,
        '.o_AttachmentCard_asideItemUnlink',
        "attachment should have a delete button"
    );

    await click('.o_AttachmentCard_asideItemUnlink');
    assert.containsOnce(
        document.body,
        '.o_AttachmentDeleteConfirm',
        "A confirmation dialog should have been opened"
    );
    assert.strictEqual(
        document.querySelector('.o_AttachmentDeleteConfirm_mainText').textContent,
        `Do you really want to delete "Blah.txt"?`,
        "Confirmation dialog should contain the attachment delete confirmation text"
    );

    // Confirm the deletion
    await click('.o_AttachmentDeleteConfirm_confirmButton');
    assert.containsNone(
        document.body,
        '.o_AttachmentCard',
        "should no longer have an attachment",
    );
});

QUnit.test("scroll to attachment box when toggling on", async function (assert) {
    patchUiSize({ size: SIZES.XXL });
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    for (let i = 0; i < 30; i++) {
        pyEnv["mail.message"].create({
            body: "not empty".repeat(50),
            model: "res.partner",
            res_id: partnerId,
        });
    }
    pyEnv["ir.attachment"].create({
        mimetype: "text/plain",
        name: "Blah.txt",
        res_id: partnerId,
        res_model: "res.partner",
    });
    const { click, openView } = await start();
    await openView({
        res_id: partnerId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    $(".o_Chatter_scrollPanel").scrollTop(10 * 1000); // to bottom
    await nextAnimationFrame();
    await click(".o_ChatterTopbar_buttonToggleAttachments");
    assert.strictEqual($(".o_Chatter_scrollPanel").scrollTop(), 0);
});

});
});
