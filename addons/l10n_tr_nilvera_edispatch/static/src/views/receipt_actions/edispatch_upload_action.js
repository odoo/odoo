/** @odoo-module */

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { ACTIONS_GROUP_NUMBER } from "@web/search/action_menus/action_menus";
import { isReceiptTR } from "@l10n_tr_nilvera_edispatch/views/utils/utils";
import { EdispatchUploader } from "@l10n_tr_nilvera_edispatch/views/components/edispatch_uploader";

export class EdispatchUploadAction extends Component {
    static template = "l10n_tr_nilvera_edispatch.EdispatchUploadAction";
    static components = { EdispatchUploader };
    static props = {};
}

registry.category("cogMenu").add(
    "l10n-tr-edispatch-upload",
    {
        Component: EdispatchUploadAction,
        groupNumber: ACTIONS_GROUP_NUMBER,
        isDisplayed: isReceiptTR,
    },
    { sequence: 11 }
);
