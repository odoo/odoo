/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart} from "@odoo/owl";

export class PayrollDashboardActionBox extends Component {
    setup() {
        this.actionService = useService("action");
        this.rpc = useService("rpc");
        this.state = useState({
            loading: true,
            warnings: {},
        })
        onWillStart(() => {
          this.rpc('get_payroll_warnings').then(data => {
              this.state.warnings = data;
              this.state.loading = false;
            }
          )
          return Promise.resolve(true);
        })
    }
}

PayrollDashboardActionBox.template = 'hr_payroll.ActionBox';
