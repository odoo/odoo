import { _t } from "@web/core/l10n/translation";
import { markup } from "@odoo/owl";
import { registry } from "@web/core/registry";

export class AccountMoveService {
    constructor(env, services) {
        this.setup(env, services);
    }

    setup(env, services) {
        this.env = env;
        this.action = services.action;
        this.dialog = services.dialog;
        this.orm = services.orm;
    }

    async getDeletionDialogBody(body, moveIds) {
        const isMoveEndOfChain = await this.orm.call("account.move", "check_move_sequence_chain", [moveIds]);
        if (!isMoveEndOfChain) {
            const message = _t("This operation will create a gap in the sequence.");
            return markup`<div class="text-danger">${message}</div>${body}`;
        }
        return body;
    }

    async downloadPdf(accountMoveId, target = "download") {
        const downloadAction = await this.orm.call(
            "account.move",
            "action_invoice_download_pdf",
            [accountMoveId, target]
        );
        await this.action.doAction(downloadAction);
    }
}

export const accountMoveService = {
    dependencies: ["action", "dialog", "orm"],
    start(env, services) {
        return new AccountMoveService(env, services);
    },
};

registry.category("services").add("account_move", accountMoveService);
