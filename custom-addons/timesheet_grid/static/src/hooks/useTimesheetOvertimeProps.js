/** @odoo-module */

import { useComponent } from "@odoo/owl";

/**
 * Hook to get the props for the timesheet overtime component use in the
 * timesheet_many2one and timesheet_avatar_many2one components.
 * (assume the hook is used in many2one grid component)
 */
export function useTimesheetOvertimeProps() {
    const comp = useComponent();
    return {
        get props() {
            if (comp.resId && comp.props.workingHours && comp.resId in comp.props.workingHours) {
                return comp.props.workingHours[comp.resId];
            } else {
                return {};
            }
        },
    };
}
