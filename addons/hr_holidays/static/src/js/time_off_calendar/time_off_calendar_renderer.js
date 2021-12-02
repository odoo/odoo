/** @odoo-module **/

import { ComponentWrapper } from 'web.OwlCompatibility';
import { TimeOffPopoverRenderer } from "./time_off_popover_renderer";

import { TimeOffDashboard } from '@hr_holidays/dashboard/time_off_dashboard';
import { TimeOffCardMobile } from '@hr_holidays/dashboard/time_off_card';

const { DateTime } = luxon;

import config from 'web.config';

export const TimeOffCalendarRenderer = TimeOffPopoverRenderer.extend({
    async willStart() {
        await this._super(...arguments);
        await this.loadDashboardData();
    },

    async start() {
        await this._super(...arguments);

        this.TimeOffDashboardWrapper = null;

        if (!config.device.isMobile) {
            this.TimeOffDashboardWrapper = new ComponentWrapper(this, TimeOffDashboard, {
                holidays: this.holidays,
                accrual_allocations: this.accrual_allocations,
                date: DateTime.now(),
            });
            await this.TimeOffDashboardWrapper.mount(this.el.parentElement, { position: 'first-child' });
            this.TimeOffDashboardWrapper.env.bus.on('date-changed', null, async (ev) => {
                await this.loadDashboardData(ev.date);
            });
        }
    },

    async _render() {
        await this._super(...arguments);
        await this.loadDashboardData();
    },

    async loadDashboardData(date) {
        date = date ? date : DateTime.now();
        const data = await this._rpc({
            model: 'hr.leave.type',
            method: 'get_days_all_request',
            context: this.state.context, // todo session.user_context ?
            kwargs: {
                date: date,
            }
        });

        this.accrual_allocations = data.accrual_allocations;
        this.holidays = data.allocations;

        if (this.TimeOffDashboardWrapper) {
            this.TimeOffDashboardWrapper.update({ holidays: this.holidays, accrual_allocations: this.accrual_allocations, date: date });
        }
    },

    async _renderFilters() {
        await this._super(...arguments);

        if (!config.device.isMobile) {
            return;
        }

        await this.loadDashboardData();
        for (const holiday of this.holidays) {
            const node = this.el.querySelector(`.o_calendar_filter_item[data-value="${holiday[3]}"] .o_cw_filter_title`);

            if (node) {
                const mobileCard = new ComponentWrapper(this, TimeOffCardMobile, { 
                    name: holiday[0],
                    data: holiday[1],
                    requires_allocation: holiday[2] === 'yes',
                    id: holiday[3],
                });
                await mobileCard.mount(node);
            }
        }
    }
});
