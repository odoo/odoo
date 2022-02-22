/** @odoo-module **/

import { Domain } from "@web/core/domain";
import { registry } from "@web/core/registry";
import { isTruthy } from "@web/core/utils/xml";
import { isRelational } from "@web/views/helpers/view_utils";
import {
    DynamicGroupList,
    DynamicRecordList,
    Group,
    RelationalModel,
} from "@web/views/relational_model";

const { EventBus } = owl;

const QUICK_CREATE_FIELD_TYPES = ["char", "boolean", "many2one", "selection"];
const DEFAULT_QUICK_CREATE_VIEW = {
    form: {
        // note: the required modifier is written in the format returned by the server
        arch: /* xml */ `
            <form>
                <field name="display_name" placeholder="Title" modifiers='{"required": true}' />
            </form>`,
        fields: {
            display_name: { string: "Display name", type: "char" },
        },
    },
};

export const isAllowedDateField = (groupByField) => {
    return (
        ["date", "datetime"].includes(groupByField.type) &&
        isTruthy(groupByField.attrs.allow_group_range_value)
    );
};

const useTransaction = () => {
    const bus = new EventBus();
    let started = false;
    return {
        start: () => {
            if (started) {
                throw new Error(`Transaction in progress: commit or abort to start a new one.`);
            }
            started = true;
            bus.trigger("START");
        },
        commit: () => {
            if (!started) {
                throw new Error(`No transaction in progress.`);
            }
            started = false;
            bus.trigger("COMMIT");
        },
        abort: () => {
            if (!started) {
                throw new Error(`No transaction in progress.`);
            }
            started = false;
            bus.trigger("ABORT");
        },
        register: ({ onStart, onCommit, onAbort }) => {
            let currentData = null;
            bus.addEventListener("START", () => onStart && (currentData = onStart()));
            bus.addEventListener("COMMIT", () => onCommit && onCommit(currentData));
            bus.addEventListener("ABORT", () => onAbort && onAbort(currentData));
        },
    };
};

class KanbanGroup extends Group {
    constructor(model, params, state = {}) {
        super(...arguments);

        this.activeProgressValue = state.activeProgressValue || null;
        this.progressValues = [];
        this.model.transaction.register({
            onStart: () => ({ count: this.count, records: [...this.list.records] }),
            onAbort: ({ count, records }) => {
                this.count = count;
                this.list.records = records;
            },
        });
    }

    get hasActiveProgressValue() {
        return this.activeProgressValue !== null;
    }

    exportState() {
        return {
            ...super.exportState(),
            activeProgressValue: this.activeProgressValue,
        };
    }

    async filterProgressValue(value) {
        const { fieldName } = this.model.progressAttributes;
        const domains = [this.groupDomain];
        this.activeProgressValue = this.activeProgressValue === value ? null : value;
        if (this.hasActiveProgressValue) {
            domains.push([[fieldName, "=", this.activeProgressValue]]);
        }
        this.list.domain = Domain.and(domains).toList();

        await this.list.load();
        this.model.notify();
    }

    empty() {
        this.count = 0;
        this.activeProgressValue = null;
        this.progressValues = [];
        this.list.empty();
    }
}

class KanbanDynamicGroupList extends DynamicGroupList {
    constructor() {
        super(...arguments);

        this.quickCreateInfo = null; // Lazy loaded;
    }

    /**
     * @override
     */
    async load() {
        await this._loadWithProgressData(super.load());
    }

    canQuickCreate() {
        return (
            this.groupByField &&
            this.model.onCreate === "quick_create" &&
            (isAllowedDateField(this.groupByField) ||
                QUICK_CREATE_FIELD_TYPES.includes(this.groupByField.type))
        );
    }

    /**
     * @override
     */
    async createGroup() {
        const group = await super.createGroup(...arguments);
        group.progressValues.push({
            count: 0,
            value: false,
            string: this.model.env._t("Other"),
            color: "muted",
        });
        return group;
    }

    async quickCreate(group) {
        if (this.model.useSampleModel) {
            // Empty the groups because they contain sample data
            this.groups.map((group) => group.empty());
        }
        this.model.useSampleModel = false;
        if (!this.quickCreateInfo) {
            this.quickCreateInfo = await this._loadQuickCreateView();
        }
        group = group || this.groups[0];
        if (group.isFolded) {
            await group.toggle();
        }
        await group.list.quickCreate(
            this.quickCreateInfo.fields,
            this.groupByField.name,
            group.getServerValue()
        );
    }

    async moveRecord(dataRecordId, dataGroupId, refId, newGroupId) {
        const oldGroup = this.groups.find((g) => g.id === dataGroupId);
        const newGroup = this.groups.find((g) => g.id === newGroupId);

        if (!oldGroup || !newGroup) {
            return; // Groups have been re-rendered, old ids are ignored
        }

        this.model.transaction.start();

        // Quick update: moves the record at the right position and notifies components
        const record = oldGroup.list.records.find((r) => r.id === dataRecordId);
        const refIndex = newGroup.list.records.findIndex((r) => r.id === refId);
        newGroup.addRecord(oldGroup.removeRecord(record), refIndex >= 0 ? refIndex + 1 : 0);

        // Move from one group to another
        try {
            if (dataGroupId !== newGroupId) {
                const value = isRelational(this.groupByField) ? [newGroup.value] : newGroup.value;
                await record.update(this.groupByField.name, value);
                await record.save();
                await this._loadWithProgressData(oldGroup.load(), newGroup.load());
            }
            await newGroup.list.resequence();
        } catch (err) {
            this.model.transaction.abort();
            this.model.notify();
            throw err;
        }
        this.model.transaction.commit();
    }

    // ------------------------------------------------------------------------
    // Protected
    // ------------------------------------------------------------------------

    async _loadQuickCreateView() {
        if (this.isLoadingQuickCreate) {
            return;
        }
        this.isLoadingQuickCreate = true;
        const { quickCreateView: viewRef } = this.model;
        const { ArchParser } = registry.category("views").get("form");
        let fieldsView = DEFAULT_QUICK_CREATE_VIEW;
        if (viewRef) {
            fieldsView = await this.model.keepLast.add(
                this.model.viewService.loadViews({
                    context: { ...this.context, form_view_ref: viewRef },
                    resModel: this.resModel,
                    views: [[false, "form"]],
                })
            );
        }
        this.isLoadingQuickCreate = false;
        return new ArchParser().parse(fieldsView.form.arch, fieldsView.form.fields);
    }

    async _loadWithProgressData(...loadPromises) {
        // No progress attributes : normal load
        if (!this.model.progressAttributes) {
            return Promise.all(loadPromises);
        }

        // Progress attributes : load with progress bar data
        const { colors, fieldName, help, sumField } = this.model.progressAttributes;
        const progressPromise = this.model.orm.call(this.resModel, "read_progress_bar", [], {
            domain: this.domain,
            group_by: this.groupBy[0],
            progress_bar: {
                colors,
                field: fieldName,
                help,
                sum_field: sumField && sumField.name,
            },
            context: this.context,
        });

        const [progressData] = await Promise.all([progressPromise, ...loadPromises]);

        const progressField = this.fields[fieldName];
        /** @type {[string | false, string][]} */
        const colorEntries = Object.entries(colors);
        const selection = Object.fromEntries(progressField.selection || []);

        if (!colorEntries.some((e) => e[1] === "muted")) {
            colorEntries.push([false, "muted"]);
        }

        for (const group of this.groups) {
            group.progressValues = [];
            const groupKey = group.displayName || group.value;
            const counts = progressData[groupKey] || { false: group.count };
            const remaining = group.count - Object.values(counts).reduce((acc, c) => acc + c, 0);
            for (const [key, color] of colorEntries) {
                const count = key === false ? remaining : counts[key];
                group.progressValues.push({
                    count: count || 0,
                    value: key,
                    string: selection[String(key)] || this.model.env._t("Other"),
                    color,
                });
            }
        }
    }
}

class KanbanDynamicRecordList extends DynamicRecordList {
    async loadMore() {
        this.offset = this.records.length;
        const nextRecords = await this._loadRecords();
        for (const record of nextRecords) {
            this.addRecord(record);
        }
    }

    async cancelQuickCreate(force = false) {
        for (const record of this.records) {
            if (record.isQuickCreate && (force || !record.isDirty)) {
                this.removeRecord(record);
            }
        }
    }

    async quickCreate(activeFields, fieldName, value) {
        this.records = this.records.filter((r) => !r.isQuickCreate);
        const context = { ...this.context };
        if (fieldName) {
            context[`default_${fieldName}`] = value;
        }
        const record = await this.createRecord({ activeFields, context }, true);
        record.isQuickCreate = true;
    }

    async validateQuickCreate() {
        const record = this.records.find((r) => r.isQuickCreate);
        await record.save();
        record.isQuickCreate = false;
        await this.quickCreate(record.activeFields, null, record.context);
        return record;
    }

    empty() {
        this.records = [];
        this.count = 0;
    }
}

KanbanDynamicRecordList.DEFAULT_LIMIT = 40;

export class KanbanModel extends RelationalModel {
    setup(params, { view }) {
        super.setup(...arguments);

        this.viewService = view;

        this.onCreate = params.onCreate;
        this.quickCreateView = params.quickCreateView;
        this.progressAttributes = params.progressAttributes;
        this.defaultGroupBy = params.defaultGroupBy || false;
        this.transaction = useTransaction();
    }

    /**
     * Applies the default groupBy defined on the arch when not in a dialog.
     * @override
     */
    async load(params = {}) {
        /** @type {any} */
        const actualParams = { ...params };
        if (this.defaultGroupBy && !this.env.inDialog) {
            const groupBy = [...(params.groupby || []), this.defaultGroupBy];
            actualParams.groupBy = groupBy.slice(0, 1);
        }
        await super.load(actualParams);
    }

    /**
     * @override
     */
    hasData() {
        if (this.root.groups) {
            if (!this.root.groups.length) {
                // While we don't have any data, we want to display the column quick create and
                // example background. Return true so that we don't get sample data instead
                return true;
            }
            return this.root.groups.some((group) => group.list.records.length > 0);
        }
        return this.root.records.length > 0;
    }
}

KanbanModel.services = [...RelationalModel.services, "view"];
KanbanModel.DynamicGroupList = KanbanDynamicGroupList;
KanbanModel.DynamicRecordList = KanbanDynamicRecordList;
KanbanModel.Group = KanbanGroup;
