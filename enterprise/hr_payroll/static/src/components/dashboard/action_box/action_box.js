/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart} from "@odoo/owl";


export class PayrollDashboardActionBox extends Component {
    static template = "hr_payroll.ActionBox";
    static props = ["*"];

    setup() {
        this.actionService = useService("action");
        this.orm = useService('orm');
        this.state = useState({
            loading: true,
            warnings: {},
        })
        onWillStart(() => {
          this.orm.call('hr.payslip', 'get_dashboard_warnings').then(data => {
              this.state.warnings = data;
              this.state.loading = false;
            }
          )
          return Promise.resolve(true);
        })
    }
}
