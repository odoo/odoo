import { mailDataHelpers } from "@mail/../tests/mock_server/mail_mock_server";

import { models } from "@web/../tests/web_test_helpers";

export class MailPoll extends models.ServerModel {
    _name = "mail.poll";

    /** @param {boolean} [with_start_message_id] */
    _store_poll_fields(with_start_message_id = true) {
        const fields = [
            "allow_multiple_options",
            "create_date",
            "create_uid",
            "end_message_id",
            mailDataHelpers.Store.many("option_ids"),
            "poll_end_dt",
            "poll_question",
            "winning_option_id",
        ];
        if (with_start_message_id) {
            fields.push(mailDataHelpers.Store.one("start_message_id"));
        }
        return fields;
    }

    get _to_store_defaults() {
        return this._store_poll_fields();
    }
}
