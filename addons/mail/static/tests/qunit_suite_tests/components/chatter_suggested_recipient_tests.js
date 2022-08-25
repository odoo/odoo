/** @odoo-module **/

import { start, startServer } from '@mail/../tests/helpers/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('chatter_suggested_recipients_tests.js');

QUnit.test("suggest recipient on 'Send message' composer", async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({ display_name: "John Jane", email: "john@jane.be" });
    const resFakeId1 = pyEnv['res.fake'].create({ email_cc: "john@test.be", partner_ids: [resPartnerId1] });
    const { click, openView } = await start();
    await openView({
        res_id: resFakeId1,
        res_model: 'res.fake',
        views: [[false, 'form']],
    });
    await click(`.o_ChatterTopbar_buttonSendMessage`);
    assert.containsOnce(
        document.body,
        '.o_ComposerSuggestedRecipientList',
        "Should display a list of suggested recipients after opening the composer from 'Send message' button"
    );
});

QUnit.test("with 3 or less suggested recipients: no 'show more' button", async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({ display_name: "John Jane", email: "john@jane.be" });
    const resFakeId1 = pyEnv['res.fake'].create({ email_cc: "john@test.be", partner_ids: [resPartnerId1] });
    const { click, openView } = await start();
    await openView({
        res_id: resFakeId1,
        res_model: 'res.fake',
        views: [[false, 'form']],
    });
    await click(`.o_ChatterTopbar_buttonSendMessage`);
    assert.containsNone(
        document.body,
        '.o_ComposerSuggestedRecipientList_showMore',
        "should not display 'show more' button with 3 or less suggested recipients"
    );
});

QUnit.test("display reason for suggested recipient on mouse over", async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({ display_name: "John Jane", email: "john@jane.be" });
    const resFakeId1 = pyEnv['res.fake'].create({ partner_ids: [resPartnerId1] });
    const { click, openView } = await start();
    await openView({
        res_id: resFakeId1,
        res_model: 'res.fake',
        views: [[false, 'form']],
    });
    await click(`.o_ChatterTopbar_buttonSendMessage`);
    const partnerTitle = document.querySelector(`.o_ComposerSuggestedRecipient[data-partner-id="${resPartnerId1}"]`).getAttribute('title');
    assert.strictEqual(
        partnerTitle,
        "Add as recipient and follower (reason: Email partner)",
        "must display reason for suggested recipient on mouse over",
    );
});

QUnit.test("suggested recipient without partner are unchecked by default", async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const resFakeId1 = pyEnv['res.fake'].create({ email_cc: "john@test.be" });
    const { click, openView } = await start();
    await openView({
        res_id: resFakeId1,
        res_model: 'res.fake',
        views: [[false, 'form']],
    });
    await click(`.o_ChatterTopbar_buttonSendMessage`);
    const checkboxUnchecked = document.querySelector('.o_ComposerSuggestedRecipient:not([data-partner-id]) input[type=checkbox]');
    assert.notOk(
        checkboxUnchecked.checked,
        "suggested recipient without partner must be unchecked by default",
    );
});

QUnit.test("suggested recipient with partner are checked by default", async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({ display_name: "John Jane", email: "john@jane.be" });
    const resFakeId1 = pyEnv['res.fake'].create({ partner_ids: [resPartnerId1] });
    const { click, openView } = await start();
    await openView({
        res_id: resFakeId1,
        res_model: 'res.fake',
        views: [[false, 'form']],
    });
    await click(`.o_ChatterTopbar_buttonSendMessage`);
    const checkboxChecked = document.querySelector(`.o_ComposerSuggestedRecipient[data-partner-id="${resPartnerId1}"] input[type=checkbox]`);
    assert.ok(
        checkboxChecked.checked,
        "suggested recipient with partner must be checked by default",
    );
});

QUnit.test("more than 3 suggested recipients: display only 3 and 'show more' button", async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const [resPartnerId1, resPartnerId2, resPartnerId3, resPartnerId4] = pyEnv['res.partner'].create([
        { display_name: "John Jane", email: "john@jane.be" },
        { display_name: "Jack Jone", email: "jack@jone.be" },
        { display_name: "jack sparrow", email: "jsparrow@blackpearl.bb" },
        { display_name: "jolly Roger", email: "Roger@skullflag.com" },
    ]);
    const resFakeId1 = pyEnv['res.fake'].create({
        partner_ids: [resPartnerId1, resPartnerId2, resPartnerId3, resPartnerId4],
    });
    const { click, openView } = await start();
    await openView({
        res_id: resFakeId1,
        res_model: 'res.fake',
        views: [[false, 'form']],
    });

    await click(`.o_ChatterTopbar_buttonSendMessage`);
    assert.containsOnce(
        document.body,
        '.o_ComposerSuggestedRecipientList_showMore',
        "more than 3 suggested recipients display 'show more' button"
    );
});

QUnit.test("more than 3 suggested recipients: show all of them on click 'show more' button", async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const [resPartnerId1, resPartnerId2, resPartnerId3, resPartnerId4] = pyEnv['res.partner'].create([
        { display_name: "John Jane", email: "john@jane.be" },
        { display_name: "Jack Jone", email: "jack@jone.be" },
        { display_name: "jack sparrow", email: "jsparrow@blackpearl.bb" },
        { display_name: "jolly Roger", email: "Roger@skullflag.com" },
    ]);
    const resFakeId1 = pyEnv['res.fake'].create({
        partner_ids: [resPartnerId1, resPartnerId2, resPartnerId3, resPartnerId4],
    });
    const { click, openView } = await start();
    await openView({
        res_id: resFakeId1,
        res_model: 'res.fake',
        views: [[false, 'form']],
    });

    await click(`.o_ChatterTopbar_buttonSendMessage`);
    await click(`.o_ComposerSuggestedRecipientList_showMore`);
    assert.containsN(
        document.body,
        '.o_ComposerSuggestedRecipient',
        4,
        "more than 3 suggested recipients: show all of them on click 'show more' button"
    );
});

QUnit.test("more than 3 suggested recipients -> click 'show more' -> 'show less' button", async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const [resPartnerId1, resPartnerId2, resPartnerId3, resPartnerId4] = pyEnv['res.partner'].create([
        { display_name: "John Jane", email: "john@jane.be" },
        { display_name: "Jack Jone", email: "jack@jone.be" },
        { display_name: "jack sparrow", email: "jsparrow@blackpearl.bb" },
        { display_name: "jolly Roger", email: "Roger@skullflag.com" },
    ]);
    const resFakeId1 = pyEnv['res.fake'].create({
        partner_ids: [resPartnerId1, resPartnerId2, resPartnerId3, resPartnerId4],
    });
    const { click, openView } = await start();
    await openView({
        res_id: resFakeId1,
        res_model: 'res.fake',
        views: [[false, 'form']],
    });

    await click(`.o_ChatterTopbar_buttonSendMessage`);
    await click(`.o_ComposerSuggestedRecipientList_showMore`);
    assert.containsOnce(
        document.body,
        '.o_ComposerSuggestedRecipientList_showLess',
        "more than 3 suggested recipients -> click 'show more' -> 'show less' button"
    );
});

QUnit.test("suggested recipients list display 3 suggested recipient and 'show more' button when 'show less' button is clicked", async function (assert) {
    assert.expect(2);

    const pyEnv = await startServer();
    const [resPartnerId1, resPartnerId2, resPartnerId3, resPartnerId4] = pyEnv['res.partner'].create([
        { display_name: "John Jane", email: "john@jane.be" },
        { display_name: "Jack Jone", email: "jack@jone.be" },
        { display_name: "jack sparrow", email: "jsparrow@blackpearl.bb" },
        { display_name: "jolly Roger", email: "Roger@skullflag.com" },
    ]);
    const resFakeId1 = pyEnv['res.fake'].create({
        partner_ids: [resPartnerId1, resPartnerId2, resPartnerId3, resPartnerId4],
    });
    const { click, openView } = await start();
    await openView({
        res_id: resFakeId1,
        res_model: 'res.fake',
        views: [[false, 'form']],
    });

    await click(`.o_ChatterTopbar_buttonSendMessage`);
    await click(`.o_ComposerSuggestedRecipientList_showMore`);
    await click(`.o_ComposerSuggestedRecipientList_showLess`);
    assert.containsN(
        document.body,
        '.o_ComposerSuggestedRecipient',
        3,
        "suggested recipient list should display 3 suggested recipients after clicking on 'show less'."
    );
    assert.containsOnce(
        document.body,
        '.o_ComposerSuggestedRecipientList_showMore',
        "suggested recipient list should containt a 'show More' button after clicking on 'show less'."
    );
});

QUnit.test("suggested recipients should not be notified when posting an internal note", async function (assert) {
    assert.expect(1);

    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv['res.partner'].create({ display_name: "John Jane", email: "john@jane.be" });
    const resFakeId1 = pyEnv['res.fake'].create({ partner_ids: [resPartnerId1] });
    const { click, insertText, openView } = await start({
        async mockRPC(route, args) {
            if (route === '/mail/message/post') {
                assert.strictEqual(
                    args.post_data.partner_ids.length,
                    0,
                    "post data should not contain suggested recipients when posting an internal note"
                );
            }
        },
    });
    await openView({
        res_id: resFakeId1,
        res_model: 'res.fake',
        views: [[false, 'form']],
    });
    await click(`.o_ChatterTopbar_buttonLogNote`);
    await insertText('.o_ComposerTextInput_textarea', "Dummy Message");
    await click('.o_Composer_buttonSend');
});

});
});
