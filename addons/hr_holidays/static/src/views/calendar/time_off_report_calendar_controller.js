import { TimeOffCalendarController } from "./calendar_controller";

export class TimeOffReportCalendarController extends TimeOffCalendarController {
    async editRecord(record, context = {}) {
        return this._editRecord(record, context, { canExpand: false });
    }
}
