import { toggleFn } from "@mail/utils/common/signal";

import { signal } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { ActionDialog } from "@web/webclient/actions/action_dialog";

patch(ActionDialog.prototype, {
    setup() {
        super.setup();
        this.expanded = signal(false);
        this.toggleFn = toggleFn;
    },

    get canExpand() {
        const actionProps = this.actionProps.actionProps || {};
        return actionProps.resModel === "mail.compose.message" && actionProps.type === "form";
    },

    get size() {
        return this.expanded() ? "fs" : super.size;
    },

    get toggleSizeTitle() {
        return this.expanded() ? _t("Compress") : _t("Expand");
    },
});
