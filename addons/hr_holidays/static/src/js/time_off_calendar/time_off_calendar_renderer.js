/** @odoo-module **/

import { ComponentWrapper } from 'web.OwlCompatibility';
import { TimeOffPopoverRenderer } from "./time_off_popover_renderer";

import { TimeOffDashboard } from '@hr_holidays/dashboard/time_off_dashboard';
import { TimeOffCardMobile } from '@hr_holidays/dashboard/time_off_card';

import config from 'web.config';
import session from 'web.session';

export const TimeOffCalendarRenderer = TimeOffPopoverRenderer.extend({
    async willStart() {
        await this._super(...arguments);

        this.holidays = await this.loadDashboardData();
    },

    async start() {
        await this._super(...arguments);

        this.TimeOffDashboardWrapper = null;

        if (!config.device.isMobile) {
            this.TimeOffDashboardWrapper = new ComponentWrapper(this, TimeOffDashboard, { holidays: this.holidays });
            await this.TimeOffDashboardWrapper.mount(this.el.parentElement, { position: 'first-child' });
        }
    },

    async _render() {
        await this._super(...arguments);

        if (this.TimeOffDashboardWrapper) {
            this.holidays = await this.loadDashboardData();
            this.TimeOffDashboardWrapper.update({ holidays: this.holidays });
        }
    },

    async loadDashboardData() {
        return await this._rpc({
            model: 'hr.leave.type',
            method: 'get_days_all_request',
            context: this.state.context,
        });
    },

    async _renderFilters() {
        await this._super(...arguments);

        if (!config.device.isMobile) {
            return;
        }

        this.holidays = await this.loadDashboardData();
        for (const holiday of this.holidays) {
            const node = this.el.querySelector(`.o_calendar_filter_item[data-value="${holiday[3]}"] .o_cw_filter_title`);

            if (node) {
                const mobileCard = new ComponentWrapper(this, TimeOffCardMobile, { 
                    name: holiday[0],
                    data: holiday[1],
                    requires_allocation: holiday[2] === 'yes',
                    id: holiday[3]
                });
                await mobileCard.mount(node);
            }
        }
    }
});
