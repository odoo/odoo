
import { CalendarModel } from '@web/views/calendar/calendar_model';
import { ProjectModelMixin } from '../project_model_mixin';

export class ProjectCalendarModel extends ProjectModelMixin(CalendarModel) {
    async load(params = {}) {
        const domain = params.domain || this.meta.domain;
        params.domain = this._processSearchDomain(domain);
        return super.load(params);
    }
}
