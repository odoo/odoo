/** @odoo-module **/

import { patchUiSize } from '@mail/../tests/helpers/patch_ui_size';
import {
    start,
    startServer,
} from '@mail/../tests/helpers/test_utils';

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('discuss_mobile_mailbox_selection', {}, function () {
QUnit.module('discuss_mobile_mailbox_selection_tests.js');

QUnit.test('select another mailbox', async function (assert) {
    assert.expect(7);

    patchUiSize({ height: 360, width: 640 });
    const { click, messaging, openDiscuss } = await start();
    await openDiscuss();
    assert.containsOnce(
        document.body,
        '.o_Discuss',
        "should display discuss initially"
    );
    assert.hasClass(
        document.querySelector('.o_Discuss'),
        'o-isDeviceSmall',
        "discuss should be opened in mobile mode"
    );
    assert.containsOnce(
        document.body,
        '.o_Discuss_thread',
        "discuss should display a thread initially"
    );
    assert.strictEqual(
        document.querySelector('.o_Discuss_thread').dataset.threadLocalId,
        messaging.inbox.thread.localId,
        "inbox mailbox should be opened initially"
    );
    assert.containsOnce(
        document.body,
        `.o_DiscussMobileMailboxSelectionItem[
            data-mailbox-local-id="${messaging.starred.localId}"
        ]`,
        "should have a button to open starred mailbox"
    );

    await click(`.o_DiscussMobileMailboxSelectionItem[
        data-mailbox-local-id="${messaging.starred.localId}"]
    `);
    assert.containsOnce(
        document.body,
        '.o_Discuss_thread',
        "discuss should still have a thread after clicking on starred mailbox"
    );
    assert.strictEqual(
        document.querySelector('.o_Discuss_thread').dataset.threadLocalId,
        messaging.starred.thread.localId,
        "starred mailbox should be opened after clicking on it"
    );
});

QUnit.test('auto-select "Inbox" when discuss had channel as active thread', async function (assert) {
    assert.expect(3);

    const pyEnv = await startServer();
    const mailChannelId1 = pyEnv['mail.channel'].create({});

    patchUiSize({ height: 360, width: 640 });
    const { click, messaging, openDiscuss } = await start({
        discuss: {
            context: {
                active_id: mailChannelId1,
            },
        },
    });
    await openDiscuss({ waitUntilMessagesLoaded: false });
    assert.hasClass(
        document.querySelector('.o_MobileMessagingNavbar_tab[data-tab-id="channel"]'),
        'o-active',
        "'channel' tab should be active initially when loading discuss with channel id as active_id"
    );

    await click('.o_MobileMessagingNavbar_tab[data-tab-id="mailbox"]');
    assert.hasClass(
        document.querySelector('.o_MobileMessagingNavbar_tab[data-tab-id="mailbox"]'),
        'o-active',
        "'mailbox' tab should be selected after click on mailbox tab"
    );
    assert.hasClass(
        document.querySelector(`.o_DiscussMobileMailboxSelectionItem[data-mailbox-local-id="${
            messaging.inbox.localId
        }"]`),
        'o-active',
        "'Inbox' mailbox should be auto-selected after click on mailbox tab"
    );
});

});
});
});
