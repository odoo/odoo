/* @odoo-module */

import { x2ManyCommands } from "@web/core/orm_service";
import { intersection } from "@web/core/utils/arrays";
import { pick } from "@web/core/utils/objects";
import { completeActiveFields } from "@web/model/relational_model/utils";
import { DataPoint } from "./datapoint";
import { fromUnityToServerValues, getId, patchActiveFields } from "./utils";

import { markRaw } from "@odoo/owl";

function compareFieldValues(v1, v2, fieldType) {
    if (fieldType === "many2one") {
        v1 = v1 ? v1[1] : "";
        v2 = v2 ? v2[1] : "";
    }
    return v1 < v2;
}

function compareRecords(r1, r2, orderBy, fields) {
    const { name, asc } = orderBy[0];
    function getValue(record, fieldName) {
        return fieldName === "id" ? record.resId : record.data[fieldName];
    }
    const v1 = asc ? getValue(r1, name) : getValue(r2, name);
    const v2 = asc ? getValue(r2, name) : getValue(r1, name);
    if (compareFieldValues(v1, v2, fields[name].type)) {
        return -1;
    }
    if (compareFieldValues(v2, v1, fields[name].type)) {
        return 1;
    }
    if (orderBy.length > 1) {
        return compareRecords(r1, r2, orderBy.slice(1), fields);
    }
    return 0;
}

export class StaticList extends DataPoint {
    static type = "StaticList";

    /**
     * @param {import("./relational_model").Config} config
     * @param {Object} data
     * @param {Object} [options={}]
     * @param {Function} [options.onUpdate]
     * @param {Record} [options.parent]
     */
    setup(config, data, options = {}) {
        this._parent = options.parent;
        this._onUpdate = options.onUpdate;

        this._cache = markRaw({});
        this._commands = [];
        this._savePoint = undefined;
        this._unknownRecordCommands = {}; // tracks update commands on records we haven't fetched yet
        this._currentIds = [...this.resIds];
        this._needsReordering = false;
        this._tmpIncreaseLimit = 0;
        // In kanban and non editable list views, x2many records can be opened in a form view in
        // dialog, which may contain other fields than the kanban or list view. The next set keeps
        // tracks of records we already opened in dialog and thus for which we already modified the
        // config to add the form view's fields in activeFields.
        this._extendedRecords = new Set();

        this.records = data
            .slice(this.offset, this.limit)
            .map((r) => this._createRecordDatapoint(r));
        this.count = this.resIds.length;
        this.handleField = Object.keys(this.activeFields).find(
            (fieldName) => this.activeFields[fieldName].isHandle
        );
    }

    // -------------------------------------------------------------------------
    // Getters
    // -------------------------------------------------------------------------

    get currentIds() {
        return this._currentIds;
    }

    get editedRecord() {
        return this.records.find((record) => record.isInEdition);
    }

    get evalContext() {
        const context = this.config.context;
        return {
            context,
            uid: context.uid,
            allowed_company_ids: context.allowed_company_ids,
            parent: this._parent.evalContext,
        };
    }

    get limit() {
        return this.config.limit;
    }

    get offset() {
        return this.config.offset;
    }

    get orderBy() {
        return this.config.orderBy;
    }

    get resIds() {
        return this.config.resIds;
    }

    // -------------------------------------------------------------------------
    // Public
    // -------------------------------------------------------------------------

    /**
     * Adds a new record to an x2many relation. If params.record is given, adds
     * given record (use case: after saving the form dialog in a, e.g., non
     * editable x2many list). Otherwise, do an onchange to get the initial
     * values and create a new Record (e.g. after clicking on Add a line in an
     * editable x2many list).
     *
     * @param {Object} params
     * @param {"top"|"bottom"} [params.position]
     * @param {Object} [params.activeFields=this.activeFields]
     * @param {boolean} [params.withoutParent=false]
     */
    addNewRecord(params) {
        return this.model.mutex.exec(async () => {
            const { activeFields, context, mode, position, withoutParent } = params;
            const record = await this._createNewRecordDatapoint({
                activeFields,
                context,
                position,
                withoutParent,
                manuallyAdded: true,
                mode,
            });
            await this._addRecord(record, { position });
            await this._onUpdate({ withoutOnchange: !record._checkValidity({ silent: true }) });
            return record;
        });
    }

    canResequence() {
        return this.handleField && this.orderBy.length && this.orderBy[0].name === this.handleField;
    }

    /**
     * TODO: We should probably delete this function.
     * It is only used for the product configurator.
     * It will take a list of contexts containing default
     * values used to create the new records in the static list.
     * It will then delete the old records from the static list
     * and replace them with the new ones we have just created.
     */
    createAndReplace(contextRecords) {
        return this.model.mutex.exec(async () => {
            const proms = [];
            for (const context of contextRecords) {
                proms.push(
                    this._createNewRecordDatapoint({
                        context,
                        manuallyAdded: true,
                    })
                );
            }
            this.records = await Promise.all(proms);
            this._commands = this.records.map((record) => [
                x2ManyCommands.CREATE,
                record._virtualId,
            ]);
            this._currentIds = this.records.map((record) => record._virtualId);
        });
    }

    delete(record) {
        return this.model.mutex.exec(async () => {
            await this._applyCommands([[x2ManyCommands.DELETE, record.resId || record._virtualId]]);
            await this._onUpdate();
        });
    }

    async enterEditMode(record) {
        const canProceed = await this.leaveEditMode();
        if (canProceed) {
            await record.switchMode("edit");
        }
        return canProceed;
    }

    /**
     * This method is meant to be used in a very specific usecase: when an x2many record is viewed
     * or edited through a form view dialog (e.g. x2many kanban or non editable list). In this case,
     * the form typically contains different fields than the kanban or list, so we need to "extend"
     * the fields and activeFields. If the record opened in a form view dialog already exists, we
     * modify it's config to add the new fields. If it is a new record, we create it with the
     * extended config.
     *
     * @param {Object} params
     * @param {Object} params.activeFields
     * @param {Object} params.fields
     * @param {Object} [params.context]
     * @param {boolean} [params.withoutParent]
     * @param {string} [params.mode]
     * @param {Record} [record]
     * @returns {Record}
     */
    extendRecord(params, record) {
        return this.model.mutex.exec(async () => {
            // extend fields and activeFields of the list with those given in params
            completeActiveFields(this.config.activeFields, params.activeFields);
            Object.assign(this.fields, params.fields);
            const activeFields = { ...params.activeFields };
            for (const fieldName in this.activeFields) {
                if (fieldName in activeFields) {
                    patchActiveFields(activeFields[fieldName], this.activeFields[fieldName]);
                } else {
                    activeFields[fieldName] = this.activeFields[fieldName];
                }
            }

            if (record) {
                record._activeFieldsToRestore = { ...this.config.activeFields };
                const config = {
                    ...record.config,
                    ...params,
                    activeFields,
                };

                // case 1: the record already exists
                if (this._extendedRecords.has(record.id)) {
                    // case 1.1: the record has already been extended
                    // -> simply store a savepoint
                    this.model._updateConfig(record.config, config, { reload: false });
                    record._addSavePoint();
                    return record;
                }
                // case 1.2: the record is extended for the first time, and it now potentially has
                // more fields than before (or x2many fields displayed differently)
                // -> if it isn't a new record, load it to retrieve the values of new fields
                // -> generate default values for new fields
                // -> recursively update the config of the record and it's sub datapoints
                // -> apply the loaded values in the case of a not new record
                // -> store a savepoint
                // These operations must be done in that specific order to ensure that the model is
                // mutated only once (in a tick), and that datapoints have the correct config to
                // handle field values they receive.
                let data = {};
                if (!record.isNew) {
                    const evalContext = Object.assign({}, record.evalContext, config.context);
                    const resIds = [record.resId];
                    [data] = await this.model._loadRecords({ ...config, resIds }, evalContext);
                }
                this.model._updateConfig(record.config, config, { reload: false });
                record._applyDefaultValues();
                for (const fieldName in record.activeFields) {
                    if (["one2many", "many2many"].includes(record.fields[fieldName].type)) {
                        const list = record.data[fieldName];
                        const patch = {
                            activeFields: activeFields[fieldName].related.activeFields,
                            fields: activeFields[fieldName].related.fields,
                        };
                        for (const subRecord of Object.values(list._cache)) {
                            this.model._updateConfig(subRecord.config, patch, {
                                reload: false,
                            });
                        }
                        this.model._updateConfig(list.config, patch, { reload: false });
                    }
                }
                record._applyValues(data);
                const commands = this._unknownRecordCommands[record.resId];
                delete this._unknownRecordCommands[record.resId];
                if (commands) {
                    this._applyCommands(commands);
                }
                record._addSavePoint();
            } else {
                // case 2: the record is a new record
                // -> simply create one with the extended config
                record = await this._createNewRecordDatapoint({
                    activeFields,
                    context: params.context,
                    withoutParent: params.withoutParent,
                    manuallyAdded: true,
                });
                record._activeFieldsToRestore = { ...this.config.activeFields };
            }
            // mark the record as being extended, to go through case 1.1 next time
            this._extendedRecords.add(record.id);

            return record;
        });
    }

    forget(record) {
        return this.model.mutex.exec(async () => {
            await this._applyCommands([[x2ManyCommands.UNLINK, record.resId]]);
            await this._onUpdate();
        });
    }

    async leaveEditMode({ discard, canAbandon, validate } = {}) {
        if (this.editedRecord) {
            await this.model._askChanges(false);
        }
        return this.model.mutex.exec(async () => {
            if (this.editedRecord) {
                const isValid = this.editedRecord._checkValidity();
                if (!isValid && validate) {
                    return false;
                }
                if (canAbandon !== false && !validate) {
                    this._abandonRecords([this.editedRecord], { force: true });
                }
                // if we still have an editedRecord, it means it hasn't been abandonned
                if (this.editedRecord) {
                    if (isValid && !this.editedRecord.dirty && discard) {
                        return false;
                    }
                    if (
                        isValid ||
                        (!this.editedRecord.dirty && !this.editedRecord._manuallyAdded)
                    ) {
                        this.editedRecord._switchMode("readonly");
                    }
                }
            }
            return !this.editedRecord;
        });
    }

    linkTo(resId, serverData) {
        return this.model.mutex.exec(async () => {
            await this._applyCommands([[x2ManyCommands.LINK, resId, serverData]]);
            await this._onUpdate();
        });
    }

    unlinkFrom(resId, serverData) {
        return this.model.mutex.exec(async () => {
            await this._applyCommands([[x2ManyCommands.UNLINK, resId, serverData]]);
            await this._onUpdate();
        });
    }

    load({ limit, offset, orderBy } = {}) {
        return this.model.mutex.exec(async () => {
            if (this.editedRecord && !(await this.editedRecord.checkValidity())) {
                return;
            }
            limit = limit !== undefined ? limit : this.limit;
            offset = offset !== undefined ? offset : this.offset;
            orderBy = orderBy !== undefined ? orderBy : this.orderBy;
            return this._load({ limit, offset, orderBy });
        });
    }

    moveRecord(dataRecordId, _dataGroupId, refId, _targetGroupId) {
        return this.resequence(dataRecordId, refId);
    }

    sortBy(fieldName) {
        return this.model.mutex.exec(() => this._sortBy(fieldName));
    }

    async replaceWith(ids, { reload = false } = {}) {
        return this.model.mutex.exec(async () => {
            await this._replaceWith(ids, { reload });
            await this._onUpdate();
        });
    }

    async resequence(movedId, targetId) {
        return this.model.mutex.exec(() => this._resequence(movedId, targetId));
    }

    /**
     * This method is meant to be called when a record, which has previously been extended to be
     * displayed in a form view dialog (see @extendRecord) is saved. In this case, we may need to
     * add this record to the list (if it is a new one), and to notify the parent record of the
     * update. We may also want to sort the list.
     *
     * @param {Record} record
     */
    validateExtendedRecord(record) {
        return this.model.mutex.exec(async () => {
            if (!this._currentIds.includes(record.isNew ? record._virtualId : record.resId)) {
                // new record created, not yet in the list
                await this._addRecord(record);
            } else if (!record.dirty) {
                return;
            }
            await this._onUpdate();
            if (this.orderBy.length) {
                await this._sort();
            }
            record._restoreActiveFields();
            record._savePoint = undefined;
        });
    }

    // -------------------------------------------------------------------------
    // Protected
    // -------------------------------------------------------------------------

    _abandonRecords(records = this.records, { force } = {}) {
        for (const record of records) {
            if (record.canBeAbandoned && (force || !record._checkValidity())) {
                const virtualId = record._virtualId;
                const index = this._currentIds.findIndex((id) => id === virtualId);
                this._currentIds.splice(index, 1);
                this.records.splice(
                    this.records.findIndex((r) => r === record),
                    1
                );
                this._commands = this._commands.filter((c) => c[1] !== virtualId);
                this.count--;
                if (this._tmpIncreaseLimit > 0) {
                    this.model._updateConfig(
                        this.config,
                        { limit: this.limit - 1 },
                        { reload: false }
                    );
                    this._tmpIncreaseLimit--;
                }
            }
        }
    }

    async _addRecord(record, { position } = {}) {
        const command = [x2ManyCommands.CREATE, record._virtualId];
        if (position === "top") {
            this.records.unshift(record);
            if (this.records.length > this.limit) {
                this.records.pop();
            }
            this._currentIds.splice(this.offset, 0, record._virtualId);
            this._commands.unshift(command);
        } else if (position === "bottom") {
            this.records.push(record);
            this._currentIds.splice(this.offset + this.limit, 0, record._virtualId);
            if (this.records.length > this.limit) {
                this._tmpIncreaseLimit++;
                const nextLimit = this.limit + 1;
                this.model._updateConfig(this.config, { limit: nextLimit }, { reload: false });
            }
            this._commands.push(command);
        } else {
            const currentIds = [...this._currentIds, record._virtualId];
            if (this.orderBy.length) {
                await this._sort(currentIds);
            } else {
                if (this.records.length < this.limit) {
                    this.records.push(record);
                }
            }
            this._currentIds = currentIds;
            this._commands.push(command);
        }
        this.count++;
        this._needsReordering = true;
    }

    _addSavePoint() {
        for (const id in this._cache) {
            this._cache[id]._addSavePoint();
        }
        this._savePoint = markRaw({
            _commands: [...this._commands],
            _currentIds: [...this._currentIds],
            count: this.count,
        });
    }

    _applyCommands(commands) {
        const isOnLastPage = this.limit + this.offset >= this.count;
        const { CREATE, UPDATE, DELETE, UNLINK, LINK, SET } = x2ManyCommands;
        for (const command of commands) {
            switch (command[0]) {
                case CREATE: {
                    const virtualId = getId("virtual");
                    const record = this._createRecordDatapoint(command[2], { virtualId });
                    this.records.push(record);
                    this._commands.push([CREATE, virtualId]);
                    this._currentIds.splice(this.offset + this.limit, 0, virtualId);
                    this.count++;
                    break;
                }
                case UPDATE: {
                    const existingCommand = this._commands.find((c) => {
                        return (c[0] === CREATE || c[0] === UPDATE) && c[1] === command[1];
                    });
                    if (!existingCommand) {
                        this._commands.push([UPDATE, command[1]]);
                    }
                    const record = this._cache[command[1]];
                    if (!record) {
                        // the record isn't in the cache, it means it is on a page we haven't loaded
                        // so we say the record is "unknown", and store all update commands we
                        // receive about it in a separated structure, s.t. we can easily apply them
                        // later on after loading the record, if we ever load it.
                        if (!(command[1] in this._unknownRecordCommands)) {
                            this._unknownRecordCommands[command[1]] = [];
                        }
                        this._unknownRecordCommands[command[1]].push(command);
                    } else if (command[1] in this._unknownRecordCommands) {
                        // this case is more tricky: the record is in the cache, but it isn't loaded
                        // yet, as we are currently loading it (see below, where we load missing
                        // records for the current page)
                        this._unknownRecordCommands[command[1]].push(command);
                    } else {
                        const changes = {};
                        for (const fieldName in command[2]) {
                            if (["one2many", "many2many"].includes(this.fields[fieldName].type)) {
                                const invisible = record.activeFields[fieldName].invisible;
                                if (invisible === "True" || invisible === "1") {
                                    if (!(command[1] in this._unknownRecordCommands)) {
                                        this._unknownRecordCommands[command[1]] = [];
                                    }
                                    this._unknownRecordCommands[command[1]].push(command);
                                    continue;
                                }
                            }
                            changes[fieldName] = command[2][fieldName];
                        }
                        record._applyChanges(record._parseServerValues(changes, record.data));
                    }
                    break;
                }
                case DELETE:
                case UNLINK: {
                    if (command[0] === DELETE) {
                        if (!this._commands.find((c) => c[0] === CREATE && c[1] === command[1])) {
                            this._commands.push([DELETE, command[1]]);
                        }
                        this._commands = this._commands.filter((c) => {
                            return !(c[0] === CREATE || c[0] === UPDATE) || c[1] !== command[1];
                        });
                    } else {
                        // FORGET
                        const replaceWithIndex = this._commands.findIndex(
                            (c) => c[0] === SET && c[2].includes(command[1])
                        );
                        if (replaceWithIndex >= 0) {
                            const ids = this._commands[replaceWithIndex][2];
                            this._commands[replaceWithIndex][2] = ids.filter(
                                (id) => id !== command[1]
                            );
                        } else {
                            const linkToIndex = this._commands.findIndex(
                                (c) => c[0] === LINK && c[1] === command[1]
                            );
                            if (linkToIndex >= 0) {
                                this._commands.splice(linkToIndex, 1);
                            } else {
                                this._commands.push([UNLINK, command[1]]);
                            }
                        }
                    }
                    const record = this._cache[command[1]];
                    if (record) {
                        const index = this.records.findIndex((r) => r.id === record.id);
                        if (index >= 0) {
                            this.records.splice(index, 1);
                        }
                    }
                    const index = this._currentIds.findIndex((id) => id === command[1]);
                    this._currentIds.splice(index, 1);
                    this.count--;
                    break;
                }
                case LINK: {
                    const record = this._createRecordDatapoint({ ...command[2], id: command[1] });
                    if (!this.limit || this.records.length < this.limit) {
                        this.records.push(record);
                    }
                    this._currentIds.push(record.resId);
                    this._commands.push([command[0], command[1]]);
                    this.count++;
                    break;
                }
            }
        }
        // if we aren't on the last page, and *n* records of the current page have been removed
        // removed, the first *n* records of the next page become the last *n* ones of the current
        // page, so we need to add (and maybe load) them.
        const nbMissingRecords = this.limit - this.records.length;
        if (!isOnLastPage && nbMissingRecords > 0) {
            const lastRecordIndex = this.limit + this.offset;
            const firstRecordIndex = lastRecordIndex - nbMissingRecords;
            const nextRecordIds = this._currentIds.slice(firstRecordIndex, lastRecordIndex);
            const recordsToLoad = [];
            for (const id of nextRecordIds) {
                if (this._cache[id]) {
                    this.records.push(this._cache[id]);
                } else {
                    // id isn't in the cache, so we know it's not a virtual id
                    const record = this._createRecordDatapoint({ id }, { dontApplyCommands: true });
                    this.records.push(record);
                    recordsToLoad.push(record);
                }
            }
            const resIds = recordsToLoad.map((r) => r.resId);
            this.model._loadRecords({ ...this.config, resIds }).then((recordValues) => {
                for (let i = 0; i < recordsToLoad.length; i++) {
                    const record = recordsToLoad[i];
                    record._applyValues(recordValues[i]);
                    const commands = this._unknownRecordCommands[record.resId];
                    if (commands) {
                        delete this._unknownRecordCommands[record.resId];
                        this._applyCommands(commands);
                    }
                }
            });
        }
    }

    async _createNewRecordDatapoint(params = {}) {
        const changes = {};
        if (!params.withoutParent && this.config.relationField) {
            changes[this.config.relationField] = this._parent._getChanges();
            if (!this._parent.isNew) {
                changes[this.config.relationField].id = this._parent.resId;
            }
        }
        const values = await this.model._loadNewRecord(
            {
                resModel: this.resModel,
                activeFields: params.activeFields || this.activeFields,
                fields: this.fields,
                context: Object.assign({}, this.context, params.context),
            },
            { changes, evalContext: this.evalContext }
        );

        if (this.canResequence() && this.records.length) {
            const position = params.position || "bottom";
            const order = this.orderBy[0];
            const asc = !order || order.asc;
            let value;
            if (position === "top") {
                const isOnFirstPage = this.offset === 0;
                value = this.records[0].data[this.handleField];
                if (isOnFirstPage) {
                    if (asc) {
                        value = value > 0 ? value - 1 : 0;
                    } else {
                        value = value + 1;
                    }
                }
            } else if (position === "bottom") {
                value = this.records[this.records.length - 1].data[this.handleField];
                const isOnLastPage = this.limit + this.offset >= this.count;
                if (isOnLastPage) {
                    if (asc) {
                        value = value + 1;
                    } else {
                        value = value > 0 ? value - 1 : 0;
                    }
                }
            }
            values[this.handleField] = value;
        }
        return this._createRecordDatapoint(values, {
            mode: params.mode || "edit",
            virtualId: getId("virtual"),
            activeFields: params.activeFields,
            manuallyAdded: params.manuallyAdded,
        });
    }

    _createRecordDatapoint(data, params = {}) {
        const resId = data.id || false;
        if (!resId && !params.virtualId) {
            throw new Error("You must provide a virtualId if the record has no id");
        }
        const id = resId || params.virtualId;
        const config = {
            context: this.context,
            activeFields: params.activeFields || this.activeFields,
            resModel: this.resModel,
            fields: params.fields || this.fields,
            relationField: this.config.relationField,
            resId,
            resIds: resId ? [resId] : [],
            mode: params.mode || "readonly",
            isMonoRecord: true,
            currentCompanyId: this.currentCompanyId,
        };
        const { CREATE, UPDATE } = x2ManyCommands;
        const options = {
            parentRecord: this._parent,
            onUpdate: async ({ withoutParentUpdate }) => {
                if (!this.currentIds.includes(record.isNew ? record._virtualId : record.resId)) {
                    // the record hasn't been added to the list yet (we're currently creating it
                    // from a dialog)
                    return;
                }
                const hasCommand = this._commands.some(
                    (c) => (c[0] === CREATE || c[0] === UPDATE) && c[1] === id
                );
                if (!hasCommand) {
                    this._commands.push([UPDATE, id]);
                }
                if (this._extendedRecords.has(record.id)) {
                    // the record is edited from a dialog, so we don't want to notify the parent
                    // record to be notified at each change inside the dialog (it will be notified
                    // at the end when the dialog is saved)
                    return;
                }
                if (!withoutParentUpdate) {
                    await this._onUpdate({
                        withoutOnchange: !record._checkValidity({ silent: true }),
                    });
                }
            },
            virtualId: params.virtualId,
            manuallyAdded: params.manuallyAdded,
        };
        const record = new this.model.constructor.Record(this.model, config, data, options);
        this._cache[id] = record;
        if (!params.dontApplyCommands) {
            const commands = this._unknownRecordCommands[id];
            if (commands) {
                delete this._unknownRecordCommands[id];
                this._applyCommands(commands);
            }
        }
        return record;
    }

    _discard() {
        for (const id in this._cache) {
            this._cache[id]._discard();
        }
        if (this._savePoint) {
            this._commands = this._savePoint._commands;
            this._currentIds = this._savePoint._currentIds;
            this.count = this._savePoint.count;
            this._savePoint = undefined;
        } else {
            this._commands = [];
            this._currentIds = [...this.resIds];
            this.count = this.resIds.length;
        }
        this._unknownRecordCommands = [];
        const limit = this.limit - this._tmpIncreaseLimit;
        this._tmpIncreaseLimit = 0;
        this.model._updateConfig(this.config, { limit }, { reload: false });
        this.records = this._currentIds
            .slice(this.offset, this.limit)
            .map((resId) => this._cache[resId]);
    }

    _getCommands({ withReadonly } = {}) {
        const { CREATE, UPDATE } = x2ManyCommands;
        const commands = [];
        for (const command of this._commands) {
            if (command[0] === UPDATE && command[1] in this._unknownRecordCommands) {
                // the record has never been loaded, but we received update commands from the
                // server for it, so we need to sanitize them (as they contained unity values)
                const uCommands = this._unknownRecordCommands[command[1]];
                for (const uCommand of uCommands) {
                    const values = fromUnityToServerValues(
                        uCommand[2],
                        this.fields,
                        this.activeFields
                    );
                    commands.push([uCommand[0], uCommand[1], values]);
                }
            } else if (command[0] === CREATE || command[0] === UPDATE) {
                const record = this._cache[command[1]];
                const values = record._getChanges(record._changes, { withReadonly });
                if (command[0] === CREATE || Object.keys(values).length) {
                    commands.push([command[0], command[1], values]);
                }
            } else {
                commands.push(command);
            }
        }
        return commands;
    }

    _getResIdsToLoad(resIds, fieldNames = this.fieldNames) {
        return resIds.filter((resId) => {
            if (typeof resId === "string") {
                // this is a virtual id, we don't want to read it
                return false;
            }
            const record = this._cache[resId];
            if (!record) {
                // record hasn't been loaded yet
                return true;
            }
            // record has already been loaded -> check if we already read all orderBy fields
            fieldNames = fieldNames.filter((fieldName) => fieldName !== "id");
            return intersection(fieldNames, record.fieldNames).length !== fieldNames.length;
        });
    }

    async _load({
        limit = this.limit,
        offset = this.offset,
        orderBy = this.orderBy,
        nextCurrentIds = this._currentIds,
    } = {}) {
        const currentIds = nextCurrentIds.slice(offset, offset + limit);
        const resIds = this._getResIdsToLoad(currentIds);
        if (resIds.length) {
            const records = await this.model._loadRecords(
                { ...this.config, resIds },
                this.evalContext
            );
            for (const record of records) {
                this._createRecordDatapoint(record);
            }
        }
        this.records = currentIds.map((id) => this._cache[id]);
        this._currentIds = nextCurrentIds;
        await this.model._updateConfig(this.config, { limit, offset, orderBy }, { reload: false });
    }

    async _replaceWith(ids, { reload = false } = {}) {
        const resIds = reload ? ids : ids.filter((id) => !this._cache[id]);
        if (resIds.length) {
            const records = await this.model._loadRecords({
                ...this.config,
                resIds,
                context: this.context,
            });
            for (const record of records) {
                this._createRecordDatapoint(record);
            }
        }
        this.records = ids.map((id) => this._cache[id]);
        const updateCommandsToKeep = this._commands.filter(
            (c) => c[0] === x2ManyCommands.UPDATE && ids.includes(c[1])
        );
        this._commands = [x2ManyCommands.set(ids)].concat(updateCommandsToKeep);
        this._currentIds = [...ids];
        this.count = this._currentIds.length;
    }

    async _resequence(movedId, targetId) {
        const records = [...this.records];
        const order = this.orderBy.find((o) => o.name === this.handleField);
        const asc = !order || order.asc;

        // Find indices
        const fromIndex = records.findIndex((r) => r.id === movedId);
        let toIndex = 0;
        if (targetId !== null) {
            const targetIndex = records.findIndex((r) => r.id === targetId);
            toIndex = fromIndex > targetIndex ? targetIndex + 1 : targetIndex;
        }

        const getSequence = (rec) => rec && rec.data[this.handleField];

        // Determine what records need to be modified
        const firstIndex = Math.min(fromIndex, toIndex);
        const lastIndex = Math.max(fromIndex, toIndex) + 1;
        let reorderAll = false;
        let lastSequence = (asc ? -1 : 1) * Infinity;
        for (let index = 0; index < records.length; index++) {
            const sequence = getSequence(records[index]);
            if (
                ((index < firstIndex || index >= lastIndex) &&
                    ((asc && lastSequence >= sequence) || (!asc && lastSequence <= sequence))) ||
                (index >= firstIndex && index < lastIndex && lastSequence === sequence)
            ) {
                reorderAll = true;
            }
            lastSequence = sequence;
        }

        // Perform the resequence in the list of records
        const [record] = records.splice(fromIndex, 1);
        records.splice(toIndex, 0, record);

        // Creates the list of to modify
        let toReorder = records;
        if (!reorderAll) {
            toReorder = toReorder.slice(firstIndex, lastIndex).filter((r) => r.id !== movedId);
            if (fromIndex < toIndex) {
                toReorder.push(record);
            } else {
                toReorder.unshift(record);
            }
        }
        if (!asc) {
            toReorder.reverse();
        }

        const sequences = toReorder.map(getSequence);
        const offset = sequences.length && Math.min(...sequences);

        const proms = [];
        for (const [i, record] of Object.entries(toReorder)) {
            proms.push(
                record._update(
                    { [this.handleField]: offset + Number(i) },
                    { withoutParentUpdate: true }
                )
            );
        }
        await Promise.all(proms);

        await this._sort();
        await this._onUpdate();
    }

    async _sort(currentIds = this.currentIds, orderBy = this.orderBy) {
        const fieldNames = orderBy.map((o) => o.name);
        const resIds = this._getResIdsToLoad(currentIds, fieldNames);
        if (resIds.length) {
            const activeFields = pick(this.activeFields, ...fieldNames);
            const config = { ...this.config, resIds, activeFields };
            const records = await this.model._loadRecords(config);
            for (const record of records) {
                this._createRecordDatapoint(record, { activeFields });
            }
        }
        const allRecords = currentIds.map((id) => this._cache[id]);
        const sortedRecords = allRecords.sort((r1, r2) => {
            return compareRecords(r1, r2, orderBy, this.fields);
        });
        await this._load({
            orderBy,
            nextCurrentIds: sortedRecords.map((r) => r.resId || r._virtualId),
        });
        this._needsReordering = false;
    }

    async _sortBy(fieldName) {
        let orderBy = [...this.orderBy];
        if (fieldName) {
            if (orderBy.length && orderBy[0].name === fieldName) {
                if (!this._needsReordering) {
                    orderBy[0] = { name: orderBy[0].name, asc: !orderBy[0].asc };
                }
            } else {
                orderBy = orderBy.filter((o) => o.name !== fieldName);
                orderBy.unshift({
                    name: fieldName,
                    asc: true,
                });
            }
        }
        return this._sort(this._currentIds, orderBy);
    }

    _updateContext(context) {
        Object.assign(this.context, context);
        for (const record of Object.values(this._cache)) {
            record._updateChildrenContext();
        }
    }
}
