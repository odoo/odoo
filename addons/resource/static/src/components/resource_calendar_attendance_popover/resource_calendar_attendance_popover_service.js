import { addFieldDependencies, extractFieldsFromArchInfo } from "@web/model/relational_model/utils";
import { FormArchParser } from "@web/views/form/form_arch_parser";
import { parseXML } from "@web/core/utils/xml";
import { registry } from "@web/core/registry";

export class ResourceCalendarAttendancePopoverService {
    constructor(env, { orm, action, view }) {
        this.env = env;
        this.orm = orm;
        this.actionService = action;
        this.viewService = view;
    }

    setup(meta, additionalFields) {
        this.meta = meta;
        this.env.isReady.then(() => this.loadPopoverView(additionalFields));
    }

    /**
     * Load the work entry popover view and extract the recordProps and archInfo.
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

export const resourceCalendarAttendancePopoverService = {
    dependencies: ["action", "orm", "view"],
    async start(env, services) {
        return new ResourceCalendarAttendancePopoverService(env, services);
    },
};

registry
    .category("services")
    .add("resourceCalendarAttendancePopoverService", resourceCalendarAttendancePopoverService);
