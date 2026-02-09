import { useState } from "@web/owl2/utils";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { ActionDialog } from "@web/webclient/actions/action_dialog";

patch(ActionDialog.prototype, {
    setup() {
        super.setup();
        this.expanded = useState({ value: false });
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
