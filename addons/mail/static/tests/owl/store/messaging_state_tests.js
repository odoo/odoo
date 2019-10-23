odoo.define('mail.store.StateTests', function (require) {
'use strict';

const {
    afterEach: utilsAfterEach,
    beforeEach: utilsBeforeEach,
    start: utilsStart,
} = require('mail.owl.testUtils');

QUnit.module('mail.owl', {}, function () {
QUnit.module('store', {}, function () {
QUnit.module('State', {
    beforeEach() {
        utilsBeforeEach(this);
        this.start = async params => {
            if (this.widget) {
                this.widget.destroy();
            }
            const { env, widget } = await utilsStart(Object.assign({}, params, {
                data: this.data,
            }));
            this.env = env;
            this.widget = widget;
        };
    },
    afterEach() {
        utilsAfterEach(this);
        this.env = undefined;
        if (this.widget) {
            this.widget.destroy();
            this.widget = undefined;
        }
    }
});

QUnit.test("current partner", async function (assert) {
    assert.expect(6);

    await this.start({
        session: {
            name: "Admin",
            partner_id: 3,
            partner_display_name: "Your Company, Admin",
            uid: 2,
        },
    });
    assert.strictEqual(this.env.store.state.currentPartnerLocalId, 'res.partner_3');
    const currentPartner = this.env.store.state.partners[this.env.store.state.currentPartnerLocalId];
    assert.strictEqual(currentPartner.display_name, "Your Company, Admin");
    assert.strictEqual(currentPartner.id, 3);
    assert.strictEqual(currentPartner.localId, 'res.partner_3');
    assert.strictEqual(currentPartner.name, "Admin");
    assert.strictEqual(currentPartner.userId, 2);
});

QUnit.test("inbox & starred mailboxes", async function (assert) {
    assert.expect(12);

    await this.start();
    const mailboxInbox = this.env.store.state.threads['mail.box_inbox'];
    const mailboxStarred = this.env.store.state.threads['mail.box_starred'];
    assert.ok(mailboxInbox, "should have mailbox inbox");
    assert.strictEqual(mailboxInbox._model, 'mail.box');
    assert.strictEqual(mailboxInbox.counter, 0);
    assert.strictEqual(mailboxInbox.id, 'inbox');
    assert.strictEqual(mailboxInbox.localId, 'mail.box_inbox');
    assert.strictEqual(mailboxInbox.name, "Inbox"); // language-dependent
    assert.ok(mailboxStarred, "should have mailbox starred");
    assert.strictEqual(mailboxStarred._model, 'mail.box');
    assert.strictEqual(mailboxStarred.counter, 0);
    assert.strictEqual(mailboxStarred.id, 'starred');
    assert.strictEqual(mailboxStarred.localId, 'mail.box_starred');
    assert.strictEqual(mailboxStarred.name, "Starred"); // language-dependent
});

QUnit.test("global state after default '/mail/init_messaging' RPC data", async function (assert) {
    assert.expect(1);

    await this.start({
        session: {
            partner_id: 3,
        },
    });
    assert.deepEqual(
        this.env.store.state,
        {
            isMessagingReady: true,
            attachments: {},
            cannedResponses: {},
            chatWindowManager: {
                autofocusChatWindowLocalId: undefined,
                autofocusCounter: 0,
                chatWindowInitialScrollTops: {},
                chatWindowLocalIds: [],
                computed: {
                    availableVisibleSlots: 0,
                    hidden: {
                        chatWindowLocalIds: [],
                        offset: 0,
                        isVisible: false,
                    },
                    visible: [],
                },
                notifiedAutofocusCounter: 0,
            },
            commands: {},
            composers: {},
            currentPartnerLocalId: 'res.partner_3',
            dialogManager: {
                dialogs: [],
            },
            discuss: {
                activeMobileNavbarTabId: 'mailbox',
                activeThreadLocalId: undefined,
                domain: [],
                inboxMarkAsReadCounter: 0,
                isOpen: false,
                menu_id: false,
                stringifiedDomain: '[]',
                threadInitialScrollTops: {},
            },
            globalWindow: {
                innerHeight: 1080,
                innerWidth: 1920,
            },
            isMobile: false,
            mailFailures: {},
            messages: {},
            messagingMenu: {
                activeTabId: 'all',
                isMobileNewMessageToggled: false,
                isOpen: false,
            },
            moderatedChannelIds: [],
            outOfFocusUnreadMessageCounter: 0,
            partners: {
                'res.partner_odoobot': {
                    _model: 'res.partner',
                    authorMessageLocalIds: [],
                    display_name: undefined,
                    email: undefined,
                    id: 'odoobot',
                    im_status: undefined,
                    localId: 'res.partner_odoobot',
                    name: "OdooBot",
                    userId: undefined,
                },
                'res.partner_3': {
                    _model: 'res.partner',
                    authorMessageLocalIds: [],
                    display_name: "Your Company, Admin",
                    email: undefined,
                    id: 3,
                    im_status: undefined,
                    localId: 'res.partner_3',
                    name: "Admin",
                    userId: 2,
                }
            },
            temporaryAttachmentLocalIds: {},
            threadCaches: {
                'mail.box_history_[]': {
                    currentPartnerMessagePostCounter: 0,
                    isAllHistoryLoaded: false,
                    isLoaded: false,
                    isLoading: false,
                    isLoadingMore: false,
                    localId: 'mail.box_history_[]',
                    messageLocalIds: [],
                    stringifiedDomain: '[]',
                    threadLocalId: 'mail.box_history',
                },
                'mail.box_inbox_[]': {
                    currentPartnerMessagePostCounter: 0,
                    isAllHistoryLoaded: false,
                    isLoaded: false,
                    isLoading: false,
                    isLoadingMore: false,
                    localId: 'mail.box_inbox_[]',
                    messageLocalIds: [],
                    stringifiedDomain: '[]',
                    threadLocalId: 'mail.box_inbox',
                },
                'mail.box_starred_[]': {
                    currentPartnerMessagePostCounter: 0,
                    isAllHistoryLoaded: false,
                    isLoaded: false,
                    isLoading: false,
                    isLoadingMore: false,
                    localId: 'mail.box_starred_[]',
                    messageLocalIds: [],
                    stringifiedDomain: '[]',
                    threadLocalId: 'mail.box_starred',
                }
            },
            threads: {
                'mail.box_history': {
                    _model: 'mail.box',
                    attachmentLocalIds: [],
                    cacheLocalIds: {
                        '[]': 'mail.box_history_[]',
                    },
                    channel_type: undefined,
                    composerLocalId: undefined,
                    counter: undefined,
                    create_uid: undefined,
                    custom_channel_name: undefined,
                    directPartnerLocalId: undefined,
                    group_based_subscription: undefined,
                    id: 'history',
                    isPinned: true,
                    is_minimized: undefined,
                    is_moderator: undefined,
                    localId: 'mail.box_history',
                    mass_mailing: undefined,
                    memberLocalIds: [],
                    members: [],
                    messageLocalIds: [],
                    message_needaction_counter: undefined,
                    message_unread_counter: undefined,
                    moderation: undefined,
                    name: "History",
                    public: undefined,
                    seen_message_id: undefined,
                    seen_partners_info: undefined,
                    state: undefined,
                    typingMemberLocalIds: [],
                    uuid: undefined,
                },
                'mail.box_inbox': {
                    _model: 'mail.box',
                    attachmentLocalIds: [],
                    cacheLocalIds: {
                        '[]': 'mail.box_inbox_[]',
                    },
                    channel_type: undefined,
                    composerLocalId: undefined,
                    counter: 0,
                    create_uid: undefined,
                    custom_channel_name: undefined,
                    directPartnerLocalId: undefined,
                    group_based_subscription: undefined,
                    id: 'inbox',
                    isPinned: true,
                    is_minimized: undefined,
                    is_moderator: undefined,
                    localId: 'mail.box_inbox',
                    mass_mailing: undefined,
                    memberLocalIds: [],
                    members: [],
                    messageLocalIds: [],
                    message_needaction_counter: undefined,
                    message_unread_counter: undefined,
                    moderation: undefined,
                    name: "Inbox",
                    public: undefined,
                    seen_message_id: undefined,
                    seen_partners_info: undefined,
                    state: undefined,
                    typingMemberLocalIds: [],
                    uuid: undefined,
                },
                'mail.box_starred': {
                    _model: 'mail.box',
                    attachmentLocalIds: [],
                    cacheLocalIds: {
                        '[]': 'mail.box_starred_[]',
                    },
                    channel_type: undefined,
                    composerLocalId: undefined,
                    counter: 0,
                    create_uid: undefined,
                    custom_channel_name: undefined,
                    directPartnerLocalId: undefined,
                    group_based_subscription: undefined,
                    id: 'starred',
                    isPinned: true,
                    is_minimized: undefined,
                    is_moderator: undefined,
                    localId: 'mail.box_starred',
                    mass_mailing: undefined,
                    memberLocalIds: [],
                    members: [],
                    messageLocalIds: [],
                    message_needaction_counter: undefined,
                    message_unread_counter: undefined,
                    moderation: undefined,
                    name: "Starred",
                    public: undefined,
                    seen_message_id: undefined,
                    seen_partners_info: undefined,
                    state: undefined,
                    typingMemberLocalIds: [],
                    uuid: undefined,
                }
            }
        }
    );
});

});
});
});
