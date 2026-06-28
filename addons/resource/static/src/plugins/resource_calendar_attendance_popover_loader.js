import { addFieldDependencies, extractFieldsFromArchInfo } from "@web/model/relational_model/utils";
import { FormArchParser } from "@web/views/form/form_arch_parser";
import { parseXML } from "@web/core/utils/xml";
import { ResourceCalendarAttendancePopover } from "@resource/components/resource_calendar_attendance_popover/resource_calendar_attendance_popover";
import { config, types as t, Plugin, whenReady } from "@odoo/owl";

export class ResourceCalendarAttendancePopoverLoader extends Plugin {
    component = ResourceCalendarAttendancePopover;

    setup() {
        this.meta = config("meta", t.object());
        this.env = config("env", t.object());
        this.viewService = this.env.services.view;
        whenReady(() => this.loadPopoverView(this.component.additionalFieldsToFetch));
    }

    /**
     * Load the resource popover view and extract the recordProps and archInfo.
     * @param additionalFieldsToFetch
     */
    async loadPopoverView(additionalFieldsToFetch) {
        const { context, resModel, multiCreateView } = this.meta;
        const { fields, relatedModels, views } = await this.viewService.loadViews({
            context: { ...context, form_view_ref: multiCreateView },
            resModel,
            views: [[false, "form"]],
        });
        const parser = new FormArchParser();
        const arch = views.form.arch;
        this.archInfo = parser.parse(parseXML(arch), relatedModels, resModel);
        const { activeFields } = extractFieldsFromArchInfo(this.archInfo, fields);
        addFieldDependencies(activeFields, fields, additionalFieldsToFetch);
        this.recordProps = { resModel, fields, activeFields, context };
    }
}
