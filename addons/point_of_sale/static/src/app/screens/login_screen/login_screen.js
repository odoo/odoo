import { registry } from "@web/core/registry";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { Component, useProps, t } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useTime } from "@point_of_sale/app/hooks/time_hook";
import { _t } from "@web/core/l10n/translation";

export class LoginScreen extends Component {
    static template = "point_of_sale.LoginScreen";
    props = useProps({
        orderUuid: t.string().optional(),
    });
    static storeOnOrder = false;
    setup() {
        this.pos = usePos();
        this.dialog = useService("dialog");
        this.ui = useService("ui");
        this.time = useTime();
    }

    openRegister() {
        this.selectUser();
    }

    selectUser() {
        this.pos.setCashier(this.pos.user);
        this.pos.accessRight.cashierLogIn();
    }
    get backBtnName() {
        return _t("Backend");
    }
    get logoUrl() {
        return this.pos.config.receiptLogoUrl;
    }
    clickBack() {
        this.pos.closePos();
    }
}

registry.category("pos_pages").add("LoginScreen", {
    name: "LoginScreen",
    component: LoginScreen,
    route: `/pos/ui/${odoo.pos_config_id}/login`,
    params: {},
});
