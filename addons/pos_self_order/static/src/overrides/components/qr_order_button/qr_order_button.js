/** @odoo-module **/

import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useTrackedAsync } from "@point_of_sale/app/utils/hooks";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { WarningDialog } from "@web/core/errors/error_dialogs";

export class QrOrderButton extends Component {
    static template = "pos_self_order.QrOrderButton";
    static components = {};
    static props = {};

    setup() {
        this.pos = usePos();
        this.dialog = useService("dialog");
        this.doRedirectToQrForm = useTrackedAsync(() => this.redirectToQrForm());
    }

    async redirectToQrForm() {
        const user_data = await this.pos.data.call("pos.config", "get_pos_qr_order_data", [
            this.pos.config.id,
        ]);

        function addInputToForm(form, name, value) {
            const input = document.createElement("input");
            input.type = "hidden";
            input.name = name;
            input.value = value;
            form.appendChild(input);
        }

        if (user_data && user_data.success && user_data.redirect_url) {
            // Temporary form to avoid URL length issues
            const form = document.createElement("form");
            form.method = "POST";
            form.target = "_blank";
            form.action = user_data.redirect_url;
            form.style.display = "none";

            addInputToForm(form, "db_name", user_data.db_name);
            addInputToForm(form, "table_data", JSON.stringify(user_data.table_data));
            addInputToForm(form, "self_ordering_mode", user_data.self_ordering_mode);
            addInputToForm(form, "zip_archive", user_data.zip_archive);

            document.body.appendChild(form);
            form.submit();
            document.body.removeChild(form);
        } else {
            this.dialog.add(WarningDialog, {
                title: _t("Get QR codes"),
                message: _t(
                    "Enable QR menu in the Restaurant settings to get QR codes for free on tables."
                ),
            });
        }
    }
}
