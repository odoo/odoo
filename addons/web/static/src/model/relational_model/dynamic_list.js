// @ts-check
/** @odoo-module native */

import { makeLogger } from "@web/core/debug/debug_logger";
import { isX2Many } from "@web/core/field_types";
import { x2ManyCommands } from "@web/core/network/commands";
import { _t } from "@web/core/translation";
import { unique } from "@web/core/utils/collections/arrays";
import { Operation } from "@web/core/utils/operation";

import { getKnownValuesKwargs } from "./concurrency_baseline.js";
import { EditableListDataPoint } from "./editable_list_datapoint.js";
import { getSpecEvalContext } from "./field_context.js";
import { getFieldsSpec } from "./field_spec.js";
import { sameMany2OneValue } from "./field_values.js";
import { RelationalRecord } from "./record.js";
import { formatServerValue } from "./record_value_transforms.js";
import { resequenceRecords } from "./resequence.js";
import { computeNextOrderBy } from "./static_list_utils.js";

/** @import { DataPoint } from "./datapoint.js" */
const DEFAULT_HANDLE_FIELD = "sequence";

/** @abstract */
/**
 * @param {{ type: string }} field
 * @param {any} value
 * @param {any} current
 * @returns {boolean}
 */
function isSameStoredValue(field, value, current) {
    if (field.type === "many2one") {
        return sameMany2OneValue(value, current);
    }
    return (
        formatServerValue(field.type, value) === formatServerValue(field.type, current)
    );
}

const log = makeLogger("web.model.list");

export class DynamicList extends EditableListDataPoint {
    /** @type {DataPoint["setup"]} */
    setup(...args) {
        super.setup(...args);
        /** @type {number} */
        this.count = 0;
        this.handleField = this._findHandleField();
        if (!this.handleField && DEFAULT_HANDLE_FIELD in this.fields) {
            this.handleField = DEFAULT_HANDLE_FIELD;
        }
        this.isDomainSelected = false;
        this._loadedFromSample = false;
    }

    /** @returns {Record<string, any>} */
    get evalContext() {
        return getSpecEvalContext(this.config);
    }

    /**
     * @abstract
     * @returns {void}
     */
    clearSampleData() {
        this._abstract("clearSampleData");
    }

    /**
     * @param {string} name
     * @returns {never}
     */
    _abstract(name) {
        throw new Error(
            `${this.constructor.name} must implement DynamicList#${name}()`,
        );
    }

    /**
     * @abstract
     * @param {number} _offset
     * @param {number} _limit
     * @param {import("@web/core/utils/order_by").OrderTerm[]} _orderBy
     * @param {import("@web/core/domain").DomainListRepr} _domain
     * @returns {Promise<any>}
     */
    loadLocked(_offset, _limit, _orderBy, _domain) {
        return this._abstract("loadLocked");
    }

    /**
     * @abstract
     * @param {(string | number)[]} _recordIds
     */
    removeRecords(_recordIds) {
        this._abstract("removeRecords");
    }

    /**
     * @abstract
     * @param {DataPoint} _dp
     * @returns {number}
     */
    _getDPresId(_dp) {
        return this._abstract("_getDPresId");
    }

    /**
     * @abstract
     * @param {DataPoint} _dp
     * @param {string} _handleField
     * @returns {any}
     */
    _getDPFieldValue(_dp, _handleField) {
        this._abstract("_getDPFieldValue");
    }

    /**
     * @abstract
     * @returns {RelationalRecord[]}
     */
    get records() {
        return this._abstract("records");
    }

    get groupBy() {
        return [];
    }

    get orderBy() {
        return this.config.orderBy;
    }

    get domain() {
        return this.config.domain;
    }

    get isRecordCountTrustable() {
        return true;
    }

    /** @returns {number} */
    get recordCount() {
        return this.count;
    }

    get limit() {
        return this.config.limit;
    }

    get offset() {
        return this.config.offset;
    }

    get selection() {
        return this.records.filter((record) => record.selected);
    }

    /** @returns {(number | false)[] | false} */
    get selectedResIds() {
        if (this.isDomainSelected || !this.selection.length) {
            return false;
        }
        return this.selection.map((record) => record.resId);
    }

    archive(isSelected) {
        return this.model.mutex.exec(() => this._toggleArchive(isSelected, true));
    }

    canResequence() {
        return !!this.handleField;
    }

    deleteRecords(records = []) {
        return this.model.mutex.exec(() => this._deleteRecords(records));
    }

    duplicateRecords(records = []) {
        return this.model.mutex.exec(() => this._duplicateRecords(records));
    }

    async enterEditMode(record) {
        log.logic("enterEditMode", () => ({
            resModel: this.resModel,
            resId: record.resId,
            already: this.editedRecord === record,
        }));
        if (this.editedRecord === record) {
            return true;
        }
        const release = this.beginEditHandover(record);
        try {
            const canProceed = await this.leaveEditMode();
            if (canProceed) {
                const tail = () => {
                    record.checkValidityLocked();
                    this.model.patchConfig(record.config, { mode: "edit" });
                };
                if (this.model.urgentSave.isActive) {
                    tail();
                } else {
                    await this.model.mutex.exec(tail);
                }
            }
            return canProceed;
        } finally {
            release();
        }
    }

    /**
     * @param {boolean} [isSelected]
     * @returns {Promise<number[]>}
     */
    async getResIds(isSelected) {
        let resIds;
        if (isSelected) {
            if (this.isDomainSelected) {
                resIds = await this.model.orm.search(this.resModel, this.domain, {
                    limit: this.model.activeIdsLimit,
                    context: this.context,
                });
            } else {
                resIds = this.selection.map((r) => r.resId);
            }
        } else {
            resIds = this.records.map((r) => r.resId);
        }
        return unique(resIds);
    }

    /**
     * @param {RelationalRecord} editedRecord
     * @param {Record<string, any>} changes
     * @param {RelationalRecord[]} selectedRecords
     * @returns {Promise<void>}
     */
    async _applyMultiEditX2ManyCommands(editedRecord, changes, selectedRecords) {
        const proms = [];
        for (const fieldName of Object.keys(changes)) {
            if (isX2Many(this.fields[fieldName])) {
                const list = editedRecord.data[fieldName];
                let commands = list.getCommands();
                if ("display_name" in list.activeFields) {
                    commands = commands.map((command) => {
                        if (command[0] === x2ManyCommands.LINK) {
                            const relRecord = list.getCachedRecord(command[1]);
                            return [
                                command[0],
                                command[1],
                                { display_name: relRecord.data.display_name },
                            ];
                        }
                        return command;
                    });
                }
                for (const record of selectedRecords) {
                    if (record !== editedRecord) {
                        proms.push(
                            record.data[fieldName].applyCommandsLocked(commands),
                        );
                    }
                }
            }
        }
        await Promise.all(proms);
    }

    /**
     * @param {RelationalRecord[]} selectedRecords
     * @param {RelationalRecord} editedRecord
     * @param {Record<string, any>} changes
     * @returns {{ validRecords: RelationalRecord[], invalidRecords: RelationalRecord[] }}
     */
    _partitionByValidity(selectedRecords, editedRecord, changes) {
        const validRecords = [];
        const invalidRecords = [];
        for (const record of selectedRecords) {
            const isEditedRecord = record === editedRecord;
            if (
                Object.keys(changes).every(
                    (fieldName) => !record.isFieldReadonly(fieldName),
                ) &&
                record.checkValidityLocked({ silent: !isEditedRecord })
            ) {
                validRecords.push(record);
            } else {
                invalidRecords.push(record);
            }
        }
        return { validRecords, invalidRecords };
    }

    /**
     * @param {RelationalRecord} editedRecord
     * @param {RelationalRecord[]} validRecords
     * @param {Record<string, any>} changes
     * @returns {() => Promise<any>}
     */
    _getMultiSaveCall(editedRecord, validRecords, changes) {
        const resIds = unique(validRecords.map((r) => r.resId));
        const kwargs = {
            context: this.context,
            specification: getFieldsSpec(
                editedRecord.activeFields,
                editedRecord.fields,
                getSpecEvalContext(editedRecord.config),
            ),
        };
        let save;
        if (Object.values(changes).some((v) => v instanceof Operation)) {
            const changesById = {};
            for (const record of validRecords) {
                changesById[record.resId] =
                    changesById[record.resId] || record.getChangesLocked();
            }
            const valsList = resIds.map((resId) => changesById[resId]);
            const multiKwargs = getKnownValuesKwargs(
                validRecords,
                Object.keys(changes),
                kwargs,
            );
            save = () =>
                this.model.orm.webSaveMulti(
                    this.resModel,
                    resIds,
                    valsList,
                    multiKwargs,
                );
        } else {
            const vals = editedRecord.getChangesLocked();
            const saveKwargs = getKnownValuesKwargs(
                validRecords,
                Object.keys(vals),
                kwargs,
            );
            save = () =>
                this.model.orm.webSave(this.resModel, resIds, vals, saveKwargs);
        }
        return save;
    }

    /**
     * @param {any[]} records
     * @param {RelationalRecord[]} validRecords
     * @returns {void}
     */
    _applyMultiSaveResult(records, validRecords) {
        const serverValuesById = Object.fromEntries(
            records.map((record) => [record.id, record]),
        );
        const siblings = this.model.similarRecordCandidates?.();
        for (const record of validRecords) {
            const serverValues = serverValuesById[/** @type {number} */ (record.resId)];
            if (!serverValues) {
                continue;
            }
            record.setData(serverValues);
            this.model.updateSimilarRecords(record, serverValues, siblings);
        }
    }

    /** @param {{ discard?: boolean }} [options] */
    async leaveEditMode({ discard } = {}) {
        if (this.model.urgentSave.isActive) {
            return this._leaveEditMode({ discard });
        }
        const editedRecord = this.editedRecord;
        if (discard) {
            this._recordToDiscard = editedRecord;
        }
        try {
            if (editedRecord) {
                await this.model.askChanges();
            }
            if (!discard && this.editedRecord) {
                await this.model.askChanges();
            }
            return await this.model.mutex.exec(() => this._leaveEditMode({ discard }));
        } finally {
            if (discard) {
                this._recordToDiscard = null;
            }
        }
    }

    load(params = {}) {
        const limit = params.limit === undefined ? this.limit : params.limit;
        const offset = params.offset === undefined ? this.offset : params.offset;
        const orderBy = params.orderBy === undefined ? this.orderBy : params.orderBy;
        const domain = params.domain === undefined ? this.domain : params.domain;
        log.pipeline("load", () => ({
            resModel: this.resModel,
            offset,
            limit,
            orderBy,
            domain,
        }));
        return this.model.mutex.exec(() =>
            this.loadLocked(offset, limit, orderBy, domain),
        );
    }

    async multiSave(record, changes) {
        return this.model.mutex.exec(() => this.multiSaveLocked(record, changes));
    }

    selectDomain(value) {
        return this.model.mutex.exec(() => this._selectDomain(value));
    }

    /** @param {string} fieldName */
    sortBy(fieldName) {
        log.logic("sortBy", () => ({
            resModel: this.resModel,
            fieldName,
            orderBy: this.orderBy,
        }));
        return this.model.mutex.exec(() => {
            const orderBy = computeNextOrderBy(fieldName, this.orderBy, false, {
                resetOrderBy: [],
            });
            return this.loadLocked(this.offset, this.limit, orderBy, this.domain);
        });
    }

    toggleSelection() {
        return this.model.mutex.exec(() => this._toggleSelection());
    }

    unarchive(isSelected) {
        return this.model.mutex.exec(() => this._toggleArchive(isSelected, false));
    }

    /** @returns {Promise<any>} */
    toggleArchiveWithConfirmation(archive, dialogProps = {}) {
        const isSelected = this.isDomainSelected || this.selection.length;
        if (archive) {
            return Promise.resolve(
                this.model.uiHooks.onConfirmArchive(
                    () => this.archive(isSelected),
                    dialogProps,
                ),
            );
        }
        return this.unarchive(isSelected);
    }

    /**
     * @param {RelationalRecord[]} records
     * @returns {Promise<number[]>}
     */
    async _resolveBulkTargets(records) {
        if (records.length) {
            return unique(/** @type {number[]} */ (records.map((r) => r.resId)));
        }
        return this.getResIds(true);
    }

    /**
     * @param {number[]} resIds
     * @param {() => string} message
     * @returns {void}
     */
    warnIfTruncated(resIds, message) {
        if (
            this.isDomainSelected &&
            resIds.length === this.model.activeIdsLimit &&
            resIds.length < this.recordCount
        ) {
            this.model.uiHooks.onDisplayLimitNotification(message());
        }
    }

    async _duplicateRecords(records) {
        const resIds = await this._resolveBulkTargets(records);

        const copy = async (resIds) => {
            const copiedRecords = await this.model.orm.call(
                this.resModel,
                "copy",
                [resIds],
                {
                    context: this.context,
                },
            );

            if (resIds.length > copiedRecords.length) {
                this.model.uiHooks.onDisplayLimitNotification(
                    _t("Some records could not be duplicated"),
                );
            }
            return this.model.load();
        };

        await this.model.uiHooks.onConfirmDuplicate(resIds, copy);
    }

    async _deleteRecords(records) {
        const resIds = await this._resolveBulkTargets(records);
        const unlinked = await this.model.orm.unlink(this.resModel, resIds, {
            context: this.context,
        });
        if (!unlinked) {
            return false;
        }
        this.warnIfTruncated(resIds, () =>
            _t(
                "Only the first %(count)s records have been deleted (out of %(total)s selected)",
                { count: resIds.length, total: this.recordCount },
            ),
        );
        await this.model.load();
        return unlinked;
    }

    /**
     * @param {{ discard?: boolean }} [options]
     * @returns {Promise<boolean>}
     */
    async _leaveEditMode({ discard } = {}) {
        let editedRecord = this.editedRecord;
        log.logic("leaveEditMode", () => ({
            resModel: this.resModel,
            resId: editedRecord?.resId,
            discard: Boolean(discard),
        }));
        if (!editedRecord) {
            return true;
        }
        let canProceed = true;
        if (discard) {
            this.model.closeUrgentSaveNotification();
            this._recordToDiscard = editedRecord;
            try {
                editedRecord.discardLocked();
            } finally {
                this._recordToDiscard = null;
            }
            editedRecord = this.editedRecord;
            if (editedRecord?.isNew) {
                this.removeRecords([editedRecord.id]);
            }
        } else {
            let isValid = true;
            if (!this.model.urgentSave.isActive) {
                isValid = editedRecord.checkValidityLocked();
            }
            if (editedRecord.isNew && !editedRecord.dirty) {
                this.removeRecords([editedRecord.id]);
            } else if (isValid || editedRecord.dirty) {
                canProceed = await editedRecord.saveLocked();
            }
        }

        editedRecord = this.editedRecord;
        if (canProceed && editedRecord) {
            this.model.patchConfig(editedRecord.config, {
                mode: "readonly",
            });
        }
        return canProceed;
    }

    async _leaveSampleMode() {
        if (this.model.useSampleModel) {
            await this.loadLocked(this.offset, this.limit, this.orderBy, this.domain);
            this.model.useSampleModel = false;
        }
    }

    /**
     * @param {import("./record").RelationalRecord} editedRecord
     * @param {Record<string, any>} changes
     * @returns {Record<string, any>}
     */
    _dropUnchangedMultiEditValues(editedRecord, changes) {
        const kept = {};
        for (const [fieldName, value] of Object.entries(changes)) {
            const field = this.fields[fieldName];
            if (
                !field ||
                isX2Many(field) ||
                !isSameStoredValue(field, value, editedRecord.data[fieldName])
            ) {
                kept[fieldName] = value;
            }
        }
        return kept;
    }

    async multiSaveLocked(editedRecord, changes) {
        changes = this._dropUnchangedMultiEditValues(editedRecord, changes);
        log.logic("multiSave", () => ({
            resModel: this.resModel,
            fields: Object.keys(changes),
            selected: this.selection?.length,
        }));
        if (!Object.keys(changes).length || editedRecord === this._recordToDiscard) {
            return;
        }
        let canProceed = await this.model.notifyLifecycle(
            "onWillSaveMulti",
            editedRecord,
            changes,
        );
        if (canProceed === false) {
            return false;
        }

        const selectedRecords = this.selection;

        await this._applyMultiEditX2ManyCommands(
            editedRecord,
            changes,
            selectedRecords,
        );

        selectedRecords.forEach((record) => {
            const perRecordChanges = { ...changes };
            for (const fieldName of Object.keys(perRecordChanges)) {
                if (isX2Many(this.fields[fieldName])) {
                    perRecordChanges[fieldName] = record.data[fieldName];
                }
            }
            record.applyChanges(perRecordChanges);
        });

        const { validRecords, invalidRecords } = this._partitionByValidity(
            selectedRecords,
            editedRecord,
            changes,
        );
        const discardInvalidRecords = () =>
            invalidRecords.forEach((record) => record.discardLocked());

        if (!validRecords.length) {
            editedRecord.displayInvalidFieldNotification();
            discardInvalidRecords();
            return false;
        }

        const save = this._getMultiSaveCall(editedRecord, validRecords, changes);

        const changesToConfirm = { ...changes };
        for (const fieldName of Object.keys(changes)) {
            if (this.fields[fieldName].type === "many2many") {
                changesToConfirm[fieldName] = changes[fieldName].stagedMembershipDelta;
            }
        }
        discardInvalidRecords();

        canProceed = await this.model.notifyLifecycle(
            "onAskMultiSaveConfirmation",
            changesToConfirm,
            validRecords,
        );
        if (canProceed === false) {
            selectedRecords.forEach((record) => record.discardLocked());
            this.leaveEditMode({ discard: true }).catch((e) => console.error(e));
            return false;
        }

        let records;
        try {
            records = await save();
        } catch (e) {
            selectedRecords.forEach((record) => record.discardLocked());
            this.model.patchConfig(editedRecord.config, { mode: "readonly" });
            throw e;
        }
        this._applyMultiSaveResult(records, validRecords);
        this.model.patchConfig(editedRecord.config, { mode: "readonly" });
        this.model.notifyLifecycle("onSavedMulti", validRecords);
        return true;
    }

    async resequenceLocked(originalList, resModel, movedId, targetId) {
        log.logic("resequence", () => ({
            resModel,
            movedId,
            targetId,
            can: this.canResequence(),
        }));
        if (this.resModel === resModel && !this.canResequence()) {
            return;
        }
        const handleField =
            this.resModel === resModel ? this.handleField : DEFAULT_HANDLE_FIELD;
        const order = this.orderBy.find((o) => o.name === handleField);
        const getSequence = (dp) => dp && this._getDPFieldValue(dp, handleField);
        const getResId = (dp) => this._getDPresId(dp);
        const resequencedRecords = await resequenceRecords({
            records: originalList,
            resModel,
            movedId,
            targetId,
            fieldName: handleField,
            asc: order?.asc,
            context: this.context,
            orm: this.model.orm,
            getSequence,
            getResId,
        });
        if (!resequencedRecords.length) {
            return;
        }
        const datapointsByResId = new Map();
        const pendingIds = new Set(resequencedRecords.map((record) => record.id));
        for (const dp of originalList) {
            const resId = getResId(dp);
            if (pendingIds.delete(resId)) {
                datapointsByResId.set(resId, dp);
            }
            if (!pendingIds.size) {
                break;
            }
        }
        for (const dpData of resequencedRecords) {
            const dp = datapointsByResId.get(dpData.id);
            if (dp instanceof RelationalRecord) {
                dp.applyValues(dpData);
            } else {
                dp[handleField] = dpData[handleField];
            }
        }
    }

    /**
     * @param {RelationalRecord} record
     * @returns {boolean}
     */
    isRecordToDiscard(record) {
        return this._recordToDiscard === record;
    }

    onRecordDeselected() {
        if (this.isDomainSelected) {
            this._selectDomain(false);
        }
    }

    _selectDomain(value) {
        this.isDomainSelected = value;
    }

    /**
     * @param {boolean} isSelected
     * @param {boolean} state
     */
    async _toggleArchive(isSelected, state) {
        const method = state ? "action_archive" : "action_unarchive";
        const context = this.context;
        const resIds = await this.getResIds(isSelected);
        const action = await this.model.orm.call(this.resModel, method, [resIds], {
            context,
        });
        this.warnIfTruncated(resIds, () =>
            _t(
                "Of the %(selectedRecords)s selected records, only the first %(firstRecords)s have been archived/unarchived.",
                {
                    selectedRecords: this.recordCount,
                    firstRecords: resIds.length,
                },
            ),
        );
        const reload = () => this.model.load();
        return this.model.uiHooks.onDisplayArchiveAction(action, reload);
    }

    async _toggleSelection() {
        const records = this.records;
        if (records.every((record) => record.selected)) {
            records.forEach((record) => {
                record._toggleSelection(false);
            });
            this._selectDomain(false);
        } else {
            records.forEach((record) => {
                record._toggleSelection(true);
            });
        }
    }
}
