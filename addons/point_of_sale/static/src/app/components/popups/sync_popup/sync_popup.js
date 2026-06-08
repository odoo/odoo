import { Dialog } from "@web/core/dialog/dialog";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

const DANGEROUS_PRODUCT_THRESHOLD = 20000;

export class SyncPopup extends Component {
    static components = { Dialog };
    static template = "point_of_sale.SyncPopup";
    static props = ["close", "confirm", "title"];

    setup() {
        this.orm = useService("orm");
        this.dialog = useService("dialog");
    }

    async confirm(fullReload) {
        if (fullReload) {
            const info = await this.orm.call("pos.config", "get_product_loading_info", [
                odoo.pos_config_id,
            ]);
            const { total_count, limit } = info;

            if (total_count > limit) {
                const isDangerous = total_count > DANGEROUS_PRODUCT_THRESHOLD;
                const title = isDangerous
                    ? _t("Dangerous: Too Many Products")
                    : _t("Large Product Count Detected");
                const body = isDangerous
                    ? _t(
                          "There are %(count)s products available for this PoS (configured limit: %(limit)s). " +
                              "Loading this many products will severely slow down the system and " +
                              "may cause it to crash or become unresponsive. " +
                              "It is strongly recommended to use Limited Synchronization instead. " +
                              "Do you still want to proceed?",
                          { count: total_count, limit }
                      )
                    : _t(
                          "There are %(count)s products available for this PoS (configured limit: %(limit)s). " +
                              "Loading all products may slow down the Point of Sale. " +
                              "Do you want to continue with Full Synchronization?",
                          { count: total_count, limit }
                      );

                this.dialog.add(ConfirmationDialog, {
                    title,
                    body,
                    confirm: () => {
                        this.props.confirm(true);
                        this.props.close();
                    },
                    cancel: () => {},
                });
                return;
            }
        }

        this.props.confirm(fullReload);
        this.props.close();
    }
}
