/** @odoo-module **/

import { HrPresenceStatus } from "@hr/components/hr_presence_status/hr_presence_status";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(HrPresenceStatus.prototype, {
    get value() {
        const originalValue = super.value;
        
        if (originalValue === 'presence_present') {
            const hasUser = this.props.record.data.user_id;
            const contractStart = this.props.record.data.contract_date_start;
            const contractEnd = this.props.record.data.contract_date_end;
            
            const hasActiveContract = contractStart && (!contractEnd || new Date(contractEnd) >= new Date());
            
            if (!hasUser && !hasActiveContract) {
                return 'presence_out_of_working_hour';
            }
        }
        
        return originalValue;
    },
    
    get label() {
        if (this.value === 'presence_present') {
            const hasUser = this.props.record.data.user_id;
            if (!hasUser) {
                return _t("Present (untracked)");
            }
        } else if (this.value === 'presence_out_of_working_hour') {
            return _t("Off-Hours");
        }
        
        return super.label;
    }
});
