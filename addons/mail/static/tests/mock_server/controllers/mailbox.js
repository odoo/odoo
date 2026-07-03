import { _resolve_messages } from "@mail/../tests/mock_server/mail_mock_server";
import { Store } from "@mail/../tests/mock_server/store";
import { registerStoreHandler } from "@mail/../tests/mock_server/store_handler";

import { Command } from "@web/../tests/web_test_helpers";

// Mirrors the store handlers of `mail/controllers/mailbox.py` (MailboxController).

function _send_bookmark_update(store, messageIds) {
    /** @type {import("mock_models").BusBus} */
    const BusBus = this.env["bus.bus"];
    /** @type {import("mock_models").MailMessage} */
    const MailMessage = this.env["mail.message"];
    /** @type {import("mock_models").ResPartner} */
    const ResPartner = this.env["res.partner"];
    if (!messageIds.length) {
        return;
    }
    const bus_store = new Store();
    for (const cur_store of [store, bus_store]) {
        for (const message_id of messageIds) {
            cur_store.add(MailMessage.browse(message_id), (r) =>
                r.attr("is_bookmarked", (m) =>
                    Boolean(m.bookmarked_partner_ids?.includes(this.env.user?.partner_id))
                )
            );
            const bus_last_id = BusBus.lastBusNotificationId;
            cur_store.add_global_values({
                bookmarkBox: {
                    counter: MailMessage._filter([
                        ["bookmarked_partner_ids", "in", [this.env.user.partner_id]],
                    ]).length,
                    counter_bus_id: bus_last_id,
                    id: "bookmark",
                    model: "mail.box",
                },
            });
        }
    }
    const [partner] = ResPartner.read(this.env.user.partner_id);
    BusBus._sendone(partner, "mail.record/insert", bus_store.as_dict());
}

registerStoreHandler(
    "add_bookmark",
    function store_add_bookmark(store, params) {
        /** @type {import("mock_models").MailMessage} */
        const MailMessage = this.env["mail.message"];
        const [message] = MailMessage.browse(params.message_id);
        MailMessage.write(message.id, {
            bookmarked_partner_ids: [Command.link(this.env.user.partner_id)],
        });
        _send_bookmark_update.call(this, store, [message.id]);
    },
    { readonly: false }
);

registerStoreHandler(
    "remove_bookmark",
    function store_remove_bookmark(store, params) {
        /** @type {import("mock_models").MailMessage} */
        const MailMessage = this.env["mail.message"];
        const [message] = MailMessage.browse(params.message_id);
        MailMessage.write(message.id, {
            bookmarked_partner_ids: [Command.unlink(this.env.user.partner_id)],
        });
        _send_bookmark_update.call(this, store, [message.id]);
    },
    { readonly: false }
);

registerStoreHandler(
    "remove_all_bookmarks",
    function store_remove_all_bookmarks(store) {
        /** @type {import("mock_models").MailMessage} */
        const MailMessage = this.env["mail.message"];
        const messages = MailMessage._filter([
            ["bookmarked_partner_ids", "in", this.env.user.partner_id],
        ]);
        MailMessage.write(
            messages.map((message) => message.id),
            { bookmarked_partner_ids: [Command.unlink(this.env.user.partner_id)] }
        );
        _send_bookmark_update.call(
            this,
            store,
            messages.map((message) => message.id)
        );
    },
    { readonly: false }
);

registerStoreHandler("/mail/inbox/messages", function store_mailbox_messages(store, params) {
    store.add_inbox_fields = true;
    _resolve_messages.call(this, store, {
        ...params.fetch_params,
        domain: [["needaction", "=", true]],
    });
});

registerStoreHandler("/mail/history/messages", function store_history_messages(store, params) {
    /** @type {import("mock_models").MailNotification} */
    const MailNotification = this.env["mail.notification"];
    _resolve_messages.call(
        this,
        store,
        {
            ...params.fetch_params,
            domain: [["needaction", "=", false]],
        },
        {
            filter(message) {
                const notifs = MailNotification.search_read([
                    ["mail_message_id", "=", message.id],
                    ["is_read", "=", true],
                    ["res_partner_id", "=", this.env.user.partner_id],
                ]);
                return notifs.length > 0;
            },
        }
    );
});

registerStoreHandler("/mail/bookmark/messages", function store_bookmark_messages(store, params) {
    _resolve_messages.call(this, store, {
        ...params.fetch_params,
        domain: [["bookmarked_partner_ids", "in", [this.env.user.partner_id]]],
    });
});
