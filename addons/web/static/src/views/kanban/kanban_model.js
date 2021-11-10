/** @odoo-module **/

import { Domain } from "@web/core/domain";
import { isRelational } from "@web/views/helpers/view_utils";
import {
    DynamicGroupList,
    DynamicRecordList,
    Group,
    RelationalModel,
} from "@web/views/relational_model";

class KanbanGroup extends Group {
    constructor(model, params, state = {}) {
        super(...arguments);

        this.activeProgressValue = state.activeProgressValue || null;
        this.isDirty = false;
        this.progressValues = [];
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
        const domains = [this.domain, this.groupDomain];
        this.activeProgressValue = this.activeProgressValue === value ? null : value;
        if (this.hasActiveProgressValue) {
            domains.push([[fieldName, "=", this.activeProgressValue]]);
        }
        this.list.domain = Domain.and(domains).toList();

        await this.list.load();
        this.model.notify();
    }
}

class KanbanDynamicGroupList extends DynamicGroupList {
    /**
     * @override
     */
    async load() {
        await this._fetchProgressData(super.load());
    }

    async moveRecord(dataRecordId, dataGroupId, refId, newGroupId) {
        const oldGroup = this.groups.find((g) => g.id === dataGroupId);
        const newGroup = this.groups.find((g) => g.id === newGroupId);

        if (!oldGroup || !newGroup) {
            return; // Groups have been re-rendered, old ids are ignored
        }

        const record = oldGroup.list.records.find((r) => r.id === dataRecordId);

        // Quick update: moves the record at the right position and notifies components
        oldGroup.list.records = oldGroup.list.records.filter((r) => r !== record);
        oldGroup.list.count--;
        oldGroup.isDirty = true;
        if (!newGroup.list.isFolded) {
            const index = refId ? newGroup.list.records.findIndex((r) => r.id === refId) + 1 : 0;
            newGroup.list.records.splice(index, 0, record);
        }
        newGroup.list.count++;
        newGroup.isDirty = true;
        newGroup.isFolded = false;
        this.model.notify();

        // move from one group to another
        if (dataGroupId !== newGroupId) {
            const value = isRelational(this.groupByField) ? [newGroup.value] : newGroup.value;
            await record.update(this.groupByField.name, value);
            await record.save();
            await this._fetchProgressData(this._reloadGroups());
            await Promise.all([oldGroup.list.load(), newGroup.list.load()]);
        }
        await newGroup.list.resequence();
    }

    async createGroup(value) {
        const [id, displayName] = await this.model.orm.call(
            this.groupByField.relation,
            "name_create",
            [value],
            { context: this.context }
        );
        const group = this.model.createDataPoint("group", {
            count: 0,
            value: id,
            displayName,
            aggregates: {},
            fields: this.fields,
            activeFields: this.activeFields,
            resModel: this.resModel,
            domain: this.domain,
            groupBy: this.groupBy.slice(1),
            context: this.context,
            orderedBy: this.orderedBy,
        });
        group.isFolded = false;
        group.progressValues.push({
            count: 0,
            value: false,
            string: this.model.env._t("Other"),
            color: "muted",
        });
        this.groups.push(group);
        this.model.notify();
    }

    async deleteGroup(group) {
        await this.model.orm.unlink(this.groupByField.relation, [group.value], this.context);
        this.groups = this.groups.filter((g) => g.id !== group.id);
    }

    // ------------------------------------------------------------------------
    // Protected
    // ------------------------------------------------------------------------

    async _fetchProgressData(loadPromise) {
        if (!this.model.progressAttributes) {
            return loadPromise;
        }
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
        const [progressData] = await Promise.all([progressPromise, loadPromise]);

        const progressField = this.fields[fieldName];
        const colorEntries = Object.entries(colors);
        const selection = Object.fromEntries(progressField.selection || []);

        if (!colorEntries.some((e) => e[1] === "muted")) {
            colorEntries.push([false, "muted"]);
        }

        for (const group of this.groups) {
            const groupKey = group.displayName || group.value;
            const counts = progressData[groupKey] || { false: group.count };
            const remaining = group.count - Object.values(counts).reduce((acc, c) => acc + c, 0);
            for (const [key, color] of colorEntries) {
                const count = key === false ? remaining : counts[key];
                group.progressValues.push({
                    count: count || 0,
                    value: key,
                    string: selection[key] || this.model.env._t("Other"),
                    color,
                });
            }
        }
    }

    async _reloadGroups() {
        const oldGroups = this.groups;
        const promises = [];
        this.groups = await this._loadGroups();
        for (const group of this.groups) {
            const previous = oldGroups.find((g) => g.value === group.value);
            if (previous) {
                group.list.records = previous.list.records;
            } else {
                promises.push(group.list.load());
            }
        }
        await Promise.all(promises);
    }
}

class KanbanDynamicRecordList extends DynamicRecordList {
    async archive() {
        const resIds = this.records.map((r) => r.resId);
        await this.model.orm.call(this.resModel, "action_archive", [resIds]);
        await this.model.load();
    }

    async unarchive() {
        const resIds = this.records.map((r) => r.resId);
        await this.model.orm.call(this.resModel, "action_unarchive", [resIds]);
        await this.model.load();
    }
}

export class KanbanModel extends RelationalModel {
    setup(params = {}) {
        super.setup(...arguments);

        this.progressAttributes = params.progressAttributes;
        this.defaultGroupBy = params.defaultGroupBy || false;
    }

    /**
     * Applies the default groupBy defined on the arch when not in a dialog.
     * @override
     */
    async load(params = {}) {
        const actualParams = { ...params };
        if (this.defaultGroupBy && !this.env.inDialog) {
            const groupBy = [...(this.groupBy || []), this.defaultGroupBy];
            actualParams.groupBy = groupBy.slice(0, 1);
        }
        await super.load(actualParams);
    }
}

KanbanModel.DynamicGroupList = KanbanDynamicGroupList;
KanbanModel.DynamicRecordList = KanbanDynamicRecordList;
KanbanModel.Group = KanbanGroup;
