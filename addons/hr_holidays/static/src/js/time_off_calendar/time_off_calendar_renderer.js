/** @odoo-module **/

import { qweb as QWeb } from 'web.core';
import config from 'web.config';

import { TimeOffPopoverRenderer } from "./time_off_popover_renderer";

export const TimeOffCalendarRenderer = TimeOffPopoverRenderer.extend({
    async _render () {
        await this._super(...arguments);
        const result = await this._rpc({
            model: 'hr.leave.type',
            method: 'get_days_all_request',
            context: this.state.context,
        });

        this.$el.parent().find('.o_calendar_mini').hide();
        this.$el.parent().find('.o_timeoff_container').remove();

        // Do not display header if there is no element to display
        if (result.length > 0) {
            if (config.device.isMobile) {
                result.forEach((data) => {
                    const elem = QWeb.render('hr_holidays.dashboard_calendar_header_mobile', {
                        timeoff: data,
                    });
                    this.$el.find('.o_calendar_filter_item[data-value=' + data[4] + '] .o_cw_filter_title').append(elem);
                });
            } else {
                const elem = QWeb.render('hr_holidays.dashboard_calendar_header', {
                    timeoffs: result,
                });
                this.$el.before(elem);

                //add popover to the information tags
                [...this.$el.parent().find('.fa-question-circle-o')].forEach((popup) => {
                    $(popup).popover({
                        trigger: 'hover',
                        html: true,
                        delay: {show: 300, hide: 0},
                        content() {
                            const data = {
                                allocated: popup.dataset.allocated,
                                approved: popup.dataset.approved,
                                planned: popup.dataset.planned,
                                left: popup.dataset.left
                            };
                            const elem_popover = QWeb.render('hr_holidays.dashboard_calendar_header_leave_type_popover', {
                                data: data,
                            });
                            return elem_popover
                        },
                    });
                });
            }
        }
    },
});
