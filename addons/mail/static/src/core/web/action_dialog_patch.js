import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { ActionDialog } from "@web/webclient/actions/action_dialog";
import { proxy } from "@odoo/owl";

patch(ActionDialog.prototype, {
    setup() {
        super.setup();
        this.expanded = proxy({ value: false });
    },

    get canExpand() {
        const actionProps = this.props.actionProps || {};
        return actionProps.resModel === "mail.compose.message" && actionProps.type === "form";
    },

    get size() {
        return this.expanded.value ? "fs" : super.size;
    },

    get toggleSizeTitle() {
        return this.expanded.value ? _t("Compress") : _t("Expand");
    },

    toggleExpand() {
        this.expanded.value = !this.expanded.value;
    },
});
