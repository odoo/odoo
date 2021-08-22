/** @odoo-module **/

import {
    afterNextRender,
    beforeEach,
} from '@mail/utils/test_utils';

import { browser } from "@web/core/browser/browser";
import { patchWithCleanup } from "@web/../tests/helpers/utils";

QUnit.module('mail', {}, function () {
QUnit.module('components', {}, function () {
QUnit.module('discuss_mobile_mailbox_selection', {}, function () {
QUnit.module('discuss_mobile_mailbox_selection_tests.js', { beforeEach });

QUnit.test('select another mailbox', async function (assert) {
    assert.expect(7);

    patchWithCleanup(browser, {
        innerHeight: 640,
        innerWidth: 360,
    });
    const { messaging, openDiscuss } = await this.start({ legacyEnv: { device: { isMobile: true } } });
    await openDiscuss();
    assert.containsOnce(
        document.body,
        '.o_Discuss',
        "should display discuss initially"
    );
    assert.hasClass(
        document.querySelector('.o_Discuss'),
        'o-mobile',
        "discuss should be opened in mobile mode"
    );
    assert.containsOnce(
        document.body,
        '.o_Discuss_thread',
        "discuss should display a thread initially"
    );
    assert.strictEqual(
        document.querySelector('.o_Discuss_thread').dataset.threadLocalId,
        messaging.inbox.localId,
        "inbox mailbox should be opened initially"
    );
    assert.containsOnce(
        document.body,
        `.o_DiscussMobileMailboxSelection_button[
            data-mailbox-local-id="${messaging.starred.localId}"
        ]`,
        "should have a button to open starred mailbox"
    );

    await afterNextRender(() =>
        document.querySelector(`.o_DiscussMobileMailboxSelection_button[
            data-mailbox-local-id="${messaging.starred.localId}"]
        `).click()
    );
    assert.containsOnce(
        document.body,
        '.o_Discuss_thread',
        "discuss should still have a thread after clicking on starred mailbox"
    );
    assert.strictEqual(
        document.querySelector('.o_Discuss_thread').dataset.threadLocalId,
        messaging.starred.localId,
        "starred mailbox should be opened after clicking on it"
    );
});

QUnit.test('auto-select "Inbox" when discuss had channel as active thread', async function (assert) {
    assert.expect(3);

    patchWithCleanup(browser, {
        innerHeight: 640,
        innerWidth: 360,
    });
    this.serverData.models['mail.channel'].records.push({ id: 20 });
    const { messaging, openDiscuss } = await this.start({ legacyEnv: { device: { isMobile: true } } });
    await openDiscuss({ activeId: 'mail.channel_20' });
    assert.hasClass(
        document.querySelector('.o_MobileMessagingNavbar_tab[data-tab-id="channel"]'),
        'o-active',
        "'channel' tab should be active initially when loading discuss with channel id as active_id"
    );

    await afterNextRender(() => document.querySelector('.o_MobileMessagingNavbar_tab[data-tab-id="mailbox"]').click());
    assert.hasClass(
        document.querySelector('.o_MobileMessagingNavbar_tab[data-tab-id="mailbox"]'),
        'o-active',
        "'mailbox' tab should be selected after click on mailbox tab"
    );
    assert.hasClass(
        document.querySelector(`.o_DiscussMobileMailboxSelection_button[data-mailbox-local-id="${
            messaging.inbox.localId
        }"]`),
        'o-active',
        "'Inbox' mailbox should be auto-selected after click on mailbox tab"
    );
});

});
});
});
