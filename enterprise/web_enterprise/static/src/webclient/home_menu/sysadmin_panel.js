/** @odoo-module **/
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class SysAdminPanel extends Component {
    static props = {};
    static template = "web_enterprise.SysAdminPanel";

    setup() {
        this.subscription = useService("enterprise_subscription");
    }

    get adminMessage() {
        return this.subscription.sysadmin.message;
    }

    get showMessage() {
        if (!this.subscription.warningType || !this.subscription.sysadmin.warning_type){
            return false;
        } else if (this.subscription.sysadmin.warning_type === 'user'){
            return true;
        } else if (this.subscription.warningType === 'admin' && this.subscription.sysadmin.warning_type === 'admin'){
            return true;
        }
        return false;
    }
}
