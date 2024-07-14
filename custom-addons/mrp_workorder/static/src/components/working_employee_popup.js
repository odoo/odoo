/** @odoo-module **/

import { MrpTimer } from "@mrp/widgets/timer";
import { useService } from "@web/core/utils/hooks";
import { parseDate } from "@web/core/l10n/dates";
import { Component, onWillStart } from "@odoo/owl";

const { DateTime } = luxon;

export class WorkingEmployeePopup extends Component {
    setup() {
        super.setup();
        this.orm = useService('orm');
        this.workorderId = this.props.popupData.workorderId;

        onWillStart(() => this._getState());
    }

    addEmployee() {
        this.props.onAddEmployee();
        this.close();
    }

    async setAdmin(employeeId) {
        await this.props.onSetAdmin(employeeId);
        await this.close();
    }

    async stopEmployee(employeeId) {
        this.props.onStopEmployee(employeeId);
        this.lines.map(l => {
            if (l.employee_id === employeeId) {
                l.ongoing = false;
                const additionalDuration = DateTime.now().diff(l.start).as("seconds") / 60;
                l.duration += additionalDuration;
            }
        });
        this.render();
    }

    startEmployee(employeeId) {
        this.props.onStartEmployee(employeeId);
        this.lines.map(l => {
            if (l.employee_id === employeeId) {
                l.start = DateTime.now();
                l.ongoing = true;
            }
        });
        this.render();
    }

    async close() {
        await this.props.onClosePopup('WorkingEmployeePopup');
    }

    async _getState() {
        const productivityLines = await this.orm.call('mrp.workcenter.productivity', 'read_group', [
            [
                ['workorder_id', '=', this.workorderId],
                ['employee_id', '!=', false],
            ],
            ['duration', 'date_start:array_agg', 'date_end:array_agg'],
            ['employee_id']
        ]);
        const now = DateTime.now();
        this.lines = productivityLines.map((pl) => {
            let duration = pl.duration;
            const ongoingTimerIndex = pl.date_end.indexOf(null);
            if (ongoingTimerIndex != -1) {
                const additionalDuration = now.diff(parseDate(pl.date_start[ongoingTimerIndex])).as("seconds") / 60;
                duration += additionalDuration;
            }
            return {
                'employee_id': pl.employee_id[0],
                'employee_name': pl.employee_id[1],
                'start': now,
                'duration': duration,
                'ongoing': pl.date_end.some(d => !d),
            };
        });
    }
}

WorkingEmployeePopup.components = { MrpTimer };
WorkingEmployeePopup.props = {
    popupData: Object,
    onAddEmployee: Function,
    onSetAdmin: Function,
    onStartEmployee: Function,
    onStopEmployee: Function,
    onClosePopup: Function,
};
WorkingEmployeePopup.template = 'mrp_workorder.WorkingEmployeePopup';
