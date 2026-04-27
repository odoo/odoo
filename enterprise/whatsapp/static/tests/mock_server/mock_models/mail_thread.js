import { mailModels } from "@mail/../tests/mail_test_helpers";

import { getKwArgs, makeKwArgs } from "@web/../tests/web_test_helpers";

export class MailThread extends mailModels.MailThread {
    /**
     * @override
     * @type {typeof mailModels.MailThread["prototype"]["_thread_to_store"]}
     */
    _thread_to_store(ids, store, fields, request_list) {
        const kwargs = getKwArgs(arguments, "ids", "store", "fields", "request_list");
        request_list = kwargs.request_list;

        /** @type {import("mock_models").WhatsAppTemplate} */
        const WhatsAppTemplate = this.env["whatsapp.template"];
        super._thread_to_store(...arguments);
        if (request_list) {
            store.add(
                this.env[this._name].browse(ids[0]),
                {
                    canSendWhatsapp:
                        WhatsAppTemplate.search_count([
                            ["model", "=", this._name],
                            ["status", "=", "approved"],
                        ]) > 0,
                },
                makeKwArgs({ as_thread: true })
            );
        }
    }
}
