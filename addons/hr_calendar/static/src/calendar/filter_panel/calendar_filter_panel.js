/** @odoo-module **/

import { CalendarFilterPanel } from "@web/views/calendar/filter_panel/calendar_filter_panel";
import { patch } from "@web/core/utils/patch";


patch(CalendarFilterPanel.prototype, {
    updateSelectCreateDialogProps(props) {
        const updatedProps = super.updateSelectCreateDialogProps(props);
        updatedProps.context = {
            search_view_ref: 'hr_calendar.view_res_partner_filter_inherit_calendar',
        };
        return updatedProps;
    }
})
