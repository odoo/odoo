import { addFieldDependencies, extractFieldsFromArchInfo } from "@web/model/relational_model/utils";
import { FormArchParser } from "@web/views/form/form_arch_parser";
import { parseXML } from "@web/core/utils/xml";
import { user } from "@web/core/user";
import { registry } from "@web/core/registry";
import { onPatched } from "@odoo/owl";

export class WorkEntryPopoverService {
    static availableWorkEntrySources = {
        resource_calendar_id: {
            field: {
                name: "resource_calendar_id",
                type: "many2one",
                relation: "resource.calendar",
            },
            hasLink: true,
        },
        category: {
            field: {
                name: "category",
                type: "selection",
            },
            expectedValue: 'absence',
            data: {
                display_name: "Public Holiday",
            },
            hasLink: false,
            sequence: 2,
        },
        is_manual: {
            field: {
                name: "is_manual",
                type: "boolean",
            },
            data: {
                display_name: "Manual entry",
            },
            hasLink: false,
            sequence: 1,
        },
    };

    constructor(env, { orm, action, view }) {
        this.env = env;
        this.orm = orm;
        this.actionService = action;
        this.viewService = view;
        this.getSource = this.getSource.bind(this);
    }

    setup(meta, additionalFields) {
        this.meta = meta;
        onPatched(async () => await this._computeSources());
        this.env.isReady.then(() => this.loadPopoverView(additionalFields));
    }

    async _computeSources() {
        this._sources = (
            await Promise.all(
                Object.values(WorkEntryPopoverService.availableWorkEntrySources).map(
                    async (s, i) => ({
                        ...s,
                        allowed: !s.group || (await user.hasGroup(s.group)),
                        __index: i,
                    })
                )
            )
        ).sort(
            (a, b) =>
                (a.sequence ?? Infinity) - (b.sequence ?? Infinity) ||
                (b.__index ?? 0) - (a.__index ?? 0)
        );
    }

    async _openRecordInAction(sourceField, record) {
        const action = await this.orm.call(
            sourceField.relation,
            "get_formview_action",
            [[record.data[sourceField.name].id]],
            { context: this.meta.context }
        );
        await this.actionService.doAction({
            ...action,
            name: record.data[sourceField.name].display_name,
            target: "new",
        });
    }

    /**
     * Load the work entry popover view and extract the recordProps and archInfo.
     * @param additionalFieldsToFetch
     */
    async loadPopoverView(additionalFieldsToFetch) {
        await this._computeSources();
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
        addFieldDependencies(activeFields, fields, [
            ...this._sources.map((s) => s.field),
            ...additionalFieldsToFetch,
        ]);
        this.recordProps = { resModel, fields, activeFields, context };
    }

    /**
     * Get the source of the work entry.
     * @param record
     */
    getSource(record) {
        for (const source of this._sources) {
            if (record.data[source.field.name] && !source.expectedValue || record.data[source.field.name] && source.expectedValue === record.data[source.field.name]) {
                if (source.hasLink && source.allowed) {
                    return {
                        field: source.field,
                        data: { ...record.data[source.field.name], ...source.data },
                        onOpen: async () => this._openRecordInAction(source.field, record),
                    };
                }
                return {
                    field: source.field,
                    data: { ...record.data[source.field.name], ...source.data },
                };
            }
        }
        return null;
    }
}

export const workEntryPopoverService = {
    dependencies: ["action", "orm", "view"],
    async start(env, services) {
        return new WorkEntryPopoverService(env, services);
    },
};

registry.category("services").add("workEntryPopoverService", workEntryPopoverService);
