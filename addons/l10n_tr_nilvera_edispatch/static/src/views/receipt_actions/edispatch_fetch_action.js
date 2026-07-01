/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { Component } from "@odoo/owl";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { ACTIONS_GROUP_NUMBER } from "@web/search/action_menus/action_menus";
import { isReceiptOrDeliveryTR } from "@l10n_tr_nilvera_edispatch/views/utils/utils";

export class EdispatchFetchAction extends Component {
    static template = "l10n_tr_nilvera_edispatch.EdispatchFetchAction";
    static components = { DropdownItem };
    static props = {};

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
    }

    async onFetch() {
        await this.orm.call(
            "stock.picking",
            "action_l10n_tr_nilvera_fetch_edispatch_purchases",
            [[]]
        );
        this.notification.add(_t("e-Dispatches fetched successfully."), { type: "success" });
        await this.action.doAction("soft_reload");
    }
}

registry.category("cogMenu").add(
    "l10n-tr-edispatch-fetch",
    {
        Component: EdispatchFetchAction,
        groupNumber: ACTIONS_GROUP_NUMBER,
        isDisplayed: isReceiptOrDeliveryTR,
    },
    { sequence: 10 }
);
