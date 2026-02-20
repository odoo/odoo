import { accountMoveUploadListView } from "@account/views/account_move_list/account_move_list_view";
import { AccountMoveListController } from "@account/views/account_move_list/account_move_list_controller";
import { registry } from "@web/core/registry";
import { Component, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class SyncWithNavBtn extends Component {
    static template = "l10n_hu_edi_receive.SyncWithNavBtn";
    static props = {};

    setup() {
        this.action = useService("action");

        onWillStart(async () => {
            this.showButton = await this.env.services.orm.call(
                "res.company",
                "l10n_hu_edi_show_nav_sync_button",
                [this.env.services.company.activeCompanyIds],
            );
        });
    }

    openWizard() {
        this.action.doAction({
            name: _t('Sync with NAV'),
            type: 'ir.actions.act_window',
            res_model: 'l10n_hu_edi.receive.bills.wizard',
            views: [[false, 'form']],
            target: 'new',
        });
    }
}

export class L10nHuEdiAccountMoveListController extends AccountMoveListController {
    static components = {
        ...AccountMoveListController.components,
        SyncWithNavBtn,
    };
}

export const l10nHuEdiAccountMoveUploadListView = {
    ...accountMoveUploadListView,
    buttonTemplate: "l10n_hu_edi_receive.ListView.Buttons",
    Controller: L10nHuEdiAccountMoveListController,
};

registry.category("views").add("l10n_hu_edi_account_move_tree", l10nHuEdiAccountMoveUploadListView);
