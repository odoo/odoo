/** @odoo-module **/

import { patchUiSize } from "@mail/../tests/helpers/patch_ui_size";
import { start, startServer } from "@mail/../tests/helpers/test_utils";

QUnit.module("mail", {}, function () {
    QUnit.module("components", {}, function () {
        QUnit.module("discuss_mobile_mailbox_selection", {}, function () {
            QUnit.module("discuss_mobile_mailbox_selection_tests.js");

            QUnit.skipRefactoring(
                'auto-select "Inbox" when discuss had channel as active thread',
                async function (assert) {
                    assert.expect(3);

                    const pyEnv = await startServer();
                    const mailChannelId1 = pyEnv["mail.channel"].create({});

                    patchUiSize({ height: 360, width: 640 });
                    const { click, messaging, openDiscuss } = await start({
                        discuss: {
                            context: {
                                active_id: mailChannelId1,
                            },
                        },
                    });
                    await openDiscuss(mailChannelId1, { waitUntilMessagesLoaded: false });
                    assert.hasClass(
                        document.querySelector(
                            '.o_MobileMessagingNavbarView_tab[data-tab-id="channel"]'
                        ),
                        "o-active",
                        "'channel' tab should be active initially when loading discuss with channel id as active_id"
                    );

                    await click('.o_MobileMessagingNavbarView_tab[data-tab-id="mailbox"]');
                    assert.hasClass(
                        document.querySelector(
                            '.o_MobileMessagingNavbarView_tab[data-tab-id="mailbox"]'
                        ),
                        "o-active",
                        "'mailbox' tab should be selected after click on mailbox tab"
                    );
                    assert.hasClass(
                        document.querySelector(
                            `.o_DiscussMobileMailboxSelectionItemView[data-mailbox-local-id="${messaging.inbox.localId}"]`
                        ),
                        "o-active",
                        "'Inbox' mailbox should be auto-selected after click on mailbox tab"
                    );
                }
            );
        });
    });
});
