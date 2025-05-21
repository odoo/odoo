import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { x2ManyCommands } from "@web/core/orm_service";
import { unique } from "@web/core/utils/arrays";
import { DataPoint } from "./datapoint";
import { Operation } from "./operation";
import { Record as RelationalRecord } from "./record";
import { getFieldsSpec, resequence } from "./utils";

/**
 * @typedef {import("./record").Record} RelationalRecord
 */

const DEFAULT_HANDLE_FIELD = "sequence";

/**
 * @abstract
 */
export class DynamicList extends DataPoint {
    /**
     * @type {DataPoint["setup"]}
     */
    setup() {
        super.setup(...arguments);
        this.handleField = Object.keys(this.activeFields).find(
            (fieldName) => this.activeFields[fieldName].isHandle
        );
        if (!this.handleField && DEFAULT_HANDLE_FIELD in this.fields) {
            this.handleField = DEFAULT_HANDLE_FIELD;
        }
        this.isDomainSelected = false;
        this.evalContext = this.context;
    }

    // -------------------------------------------------------------------------
    // Getters
    // -------------------------------------------------------------------------

    get groupBy() {
        return [];
    }

    get orderBy() {
        return this.config.orderBy;
    }

    get domain() {
        return this.config.domain;
    }

    /**
     * Be careful that this getter is costly, as it iterates over the whole list
     * of records. This property should not be accessed in a loop.
     */
    get editedRecord() {
        return this.records.find((record) => record.isInEdition);
    }

    get isRecordCountTrustable() {
        return true;
    }

    get limit() {
        return this.config.limit;
    }

    get offset() {
        return this.config.offset;
    }

    /**
     * Be careful that this getter is costly, as it iterates over the whole list
     * of records. This property should not be accessed in a loop.
     */
    get selection() {
        return this.records.filter((record) => record.selected);
    }

    // -------------------------------------------------------------------------
    // Public
    // -------------------------------------------------------------------------

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
        if (this.editedRecord === record) {
            return true;
        }
        const canProceed = await this.leaveEditMode();
        if (canProceed) {
            record._checkValidity();
            this.model._updateConfig(record.config, { mode: "edit" }, { reload: false });
        }
        return canProceed;
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

    async leaveEditMode({ discard } = {}) {
        let editedRecord = this.editedRecord;
        if (editedRecord) {
            let canProceed = true;
            if (discard) {
                this._recordToDiscard = editedRecord;
                await editedRecord.discard();
                this._recordToDiscard = null;
                editedRecord = this.editedRecord;
                if (editedRecord && editedRecord.isNew) {
                    this._removeRecords([editedRecord.id]);
                }
            } else {
                let isValid = true;
                if (!this.model._urgentSave) {
                    isValid = await editedRecord.checkValidity();
                    editedRecord = this.editedRecord;
                    if (!editedRecord) {
                        return true;
                    }
                }
                if (editedRecord.isNew && !editedRecord.dirty) {
                    this._removeRecords([editedRecord.id]);
                } else if (isValid || editedRecord.dirty) {
                    canProceed = await editedRecord.save();
                }
            }

            editedRecord = this.editedRecord;
            if (canProceed && editedRecord) {
                this.model._updateConfig(
                    editedRecord.config,
                    { mode: "readonly" },
                    { reload: false }
                );
            } else {
                return canProceed;
            }
        }
        return true;
    }

    load(params = {}) {
        const limit = params.limit === undefined ? this.limit : params.limit;
        const offset = params.offset === undefined ? this.offset : params.offset;
        const orderBy = params.orderBy === undefined ? this.orderBy : params.orderBy;
        const domain = params.domain === undefined ? this.domain : params.domain;
        return this.model.mutex.exec(() => this._load(offset, limit, orderBy, domain));
    }

    async multiSave(record, changes) {
        return this.model.mutex.exec(() => this._multiSave(record, changes));
    }

    selectDomain(value) {
        return this.model.mutex.exec(() => this._selectDomain(value));
    }

    sortBy(fieldName) {
        return this.model.mutex.exec(() => {
            let orderBy = [...this.orderBy];
            if (orderBy.length && orderBy[0].name === fieldName) {
                if (orderBy[0].asc) {
                    orderBy[0] = { name: orderBy[0].name, asc: false };
                } else {
                    orderBy = [];
                }
            } else {
                orderBy = orderBy.filter((o) => o.name !== fieldName);
                orderBy.unshift({
                    name: fieldName,
                    asc: true,
                });
            }
            return this._load(this.offset, this.limit, orderBy, this.domain);
        });
    }

    toggleSelection() {
        return this.model.mutex.exec(() => this._toggleSelection());
    }

    unarchive(isSelected) {
        return this.model.mutex.exec(() => this._toggleArchive(isSelected, false));
    }

    toggleArchiveWithConfirmation(archive, dialogProps = {}) {
        const isSelected = this.isDomainSelected || this.selection.length > 0;
        if (archive) {
            const defaultProps = {
                body: _t("Are you sure that you want to archive all the selected records?"),
                cancel: () => {},
                confirm: () => this.archive(isSelected),
                confirmLabel: _t("Archive"),
            };
            this.model.dialog.add(ConfirmationDialog, { ...defaultProps, ...dialogProps });
        } else {
            this.unarchive(isSelected);
        }
    }

    // -------------------------------------------------------------------------
    // Protected
    // -------------------------------------------------------------------------

    async _duplicateRecords(records) {
        let resIds;
        if (records.length) {
            resIds = unique(records.map((r) => r.resId));
        } else {
            resIds = await this.getResIds(true);
        }

        const copy = async (resIds) => {
            const copiedRecords = await this.model.orm.call(this.resModel, "copy", [resIds], {
                context: this.context,
            });

            if (resIds.length > copiedRecords.length) {
                this.model.notification.add(_t("Some records could not be duplicated"));
            }
            return this.model.load();
        };

        if (resIds.length > 1) {
            this.model.dialog.add(ConfirmationDialog, {
                body: _t("Are you sure that you want to duplicate all the selected records?"),
                confirm: () => copy(resIds),
                cancel: () => {},
                confirmLabel: _t("Confirm"),
            });
        } else {
            await copy(resIds);
        }
    }

    async _deleteRecords(records) {
        let resIds;
        if (records.length) {
            resIds = unique(records.map((r) => r.resId));
        } else {
            resIds = await this.getResIds(true);
            records = this.records.filter((r) => resIds.includes(r.resId));
        }
        const unlinked = await this.model.orm.unlink(this.resModel, resIds, {
            context: this.context,
        });
        if (!unlinked) {
            return false;
        }
        if (
            this.isDomainSelected &&
            resIds.length === this.model.activeIdsLimit &&
            resIds.length < this.count
        ) {
            const msg = _t(
                "Only the first %(count)s records have been deleted (out of %(total)s selected)",
                { count: resIds.length, total: this.count }
            );
            this.model.notification.add(msg);
        }
        await this.model.load();
        return unlinked;
    }

    async _leaveSampleMode() {
        if (this.model.useSampleModel) {
            await this._load(this.offset, this.limit, this.orderBy, this.domain);
            this.model.useSampleModel = false;
        }
    }

    async _multiSave(editedRecord, changes) {
        if (!Object.keys(changes).length || editedRecord === this._recordToDiscard) {
            return;
        }
        let canProceed = await this.model.hooks.onWillSaveMulti(editedRecord, changes);
        if (canProceed === false) {
            return false;
        }

        const selectedRecords = this.selection; // costly getter => compute it once

        // special treatment for x2manys: apply commands on all selected record's static lists
        const proms = [];
        for (const fieldName in changes) {
            if (["one2many", "many2many"].includes(this.fields[fieldName].type)) {
                const list = editedRecord.data[fieldName];
                const commands = list._getCommands();
                if ("display_name" in list.activeFields) {
                    // add display_name to LINK commands to prevent a web_read by selected record
                    for (const command of commands) {
                        if (command[0] === x2ManyCommands.LINK) {
                            const relRecord = list._cache[command[1]];
                            command[2] = { display_name: relRecord.data.display_name };
                        }
                    }
                }
                for (const record of selectedRecords) {
                    if (record !== editedRecord) {
                        proms.push(record.data[fieldName]._applyCommands(commands));
                    }
                }
            }
        }
        await Promise.all(proms);
        // apply changes on all selected records (for x2manys, the change is the static list itself)
        selectedRecords.forEach((record) => {
            const _changes = Object.assign({}, changes);
            for (const fieldName in _changes) {
                if (["one2many", "many2many"].includes(this.fields[fieldName].type)) {
                    _changes[fieldName] = record.data[fieldName];
                }
            }
            record._applyChanges(_changes);
        });

        // determine valid and invalid records
        const validRecords = [];
        const invalidRecords = [];
        for (const record of selectedRecords) {
            const isEditedRecord = record === editedRecord;
            if (
                Object.keys(changes).every((fieldName) => !record._isReadonly(fieldName)) &&
                record._checkValidity({ silent: !isEditedRecord })
            ) {
                validRecords.push(record);
            } else {
                invalidRecords.push(record);
            }
        }
        const discardInvalidRecords = () => invalidRecords.forEach((record) => record._discard());

        if (validRecords.length === 0) {
            editedRecord._displayInvalidFieldNotification();
            discardInvalidRecords();
            return false;
        }

        // generate the save callback with the values to save (must be done before discarding
        // invalid records, in case the editedRecord is itself invalid)
        const resIds = unique(validRecords.map((r) => r.resId));
        const kwargs = {
            context: this.context,
            specification: getFieldsSpec(editedRecord.activeFields, editedRecord.fields),
        };
        let save;
        if (Object.values(changes).some((v) => v instanceof Operation)) {
            // "changes" contains a Field Operation => we must call the web_save_multi method to
            // save each record individually
            const changesById = {};
            for (const record of validRecords) {
                changesById[record.resId] = changesById[record.resId] || record._getChanges();
            }
            const valsList = resIds.map((resId) => changesById[resId]);
            save = () => this.model.orm.webSaveMulti(this.resModel, resIds, valsList, kwargs);
        } else {
            const vals = editedRecord._getChanges();
            save = () => this.model.orm.webSave(this.resModel, resIds, vals, kwargs);
        }

        const _changes = Object.assign(changes);
        for (const fieldName in changes) {
            if (this.fields[fieldName].type === "many2many") {
                const list = changes[fieldName];
                _changes[fieldName] = {
                    add: list._commands
                        .filter((command) => command[0] === x2ManyCommands.LINK)
                        .map((command) => list._cache[command[1]]),
                    remove: list._commands
                        .filter((command) => command[0] === x2ManyCommands.UNLINK)
                        .map((command) => list._cache[command[1]]),
                };
            }
        }
        discardInvalidRecords();

        // ask confirmation
        canProceed = await this.model.hooks.onAskMultiSaveConfirmation(_changes, validRecords);
        if (canProceed === false) {
            selectedRecords.forEach((record) => record._discard());
            this.leaveEditMode({ discard: true });
            return false;
        }

        // save changes
        let records = [];
        try {
            records = await save();
        } catch (e) {
            selectedRecords.forEach((record) => record._discard());
            this.model._updateConfig(editedRecord.config, { mode: "readonly" }, { reload: false });
            throw e;
        }
        const serverValuesById = Object.fromEntries(records.map((record) => [record.id, record]));
        for (const record of validRecords) {
            const serverValues = serverValuesById[record.resId];
            record._setData(serverValues);
            this.model._updateSimilarRecords(record, serverValues);
        }
        this.model._updateConfig(editedRecord.config, { mode: "readonly" }, { reload: false });
        this.model.hooks.onSavedMulti(validRecords);
        return true;
    }

    async _resequence(originalList, resModel, movedId, targetId) {
        if (this.resModel === resModel && !this.canResequence()) {
            return;
        }
        const handleField = this.resModel === resModel ? this.handleField : DEFAULT_HANDLE_FIELD;
        const order = this.orderBy.find((o) => o.name === handleField);
        const getSequence = (dp) => dp && this._getDPFieldValue(dp, handleField);
        const getResId = (dp) => this._getDPresId(dp);
        const resequencedRecords = await resequence({
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
        for (const dpData of resequencedRecords) {
            const dp = originalList.find((d) => getResId(d) === dpData.id);
            if (dp instanceof RelationalRecord) {
                dp._applyValues(dpData);
            } else {
                dp[handleField] = dpData[handleField];
            }
        }
    }

    _selectDomain(value) {
        this.isDomainSelected = value;
    }

    async _toggleArchive(isSelected, state) {
        const method = state ? "action_archive" : "action_unarchive";
        const context = this.context;
        const resIds = await this.getResIds(isSelected);
        const action = await this.model.orm.call(this.resModel, method, [resIds], { context });
        if (
            this.isDomainSelected &&
            resIds.length === this.model.activeIdsLimit &&
            resIds.length < this.count
        ) {
            const msg = _t(
                "Of the %(selectedRecord)s selected records, only the first %(firstRecords)s have been archived/unarchived.",
                {
                    selectedRecords: resIds.length,
                    firstRecords: this.count,
                }
            );
            this.model.notification.add(msg);
        }
        const reload = () => this.model.load();
        if (action && Object.keys(action).length) {
            this.model.action.doAction(action, {
                onClose: reload,
            });
        } else {
            return reload();
        }
    }

    async _toggleSelection() {
        if (this.selection.length === this.records.length) {
            this.records.forEach((record) => {
                record._toggleSelection(false);
            });
            this._selectDomain(false);
        } else {
            this.records.forEach((record) => {
                record._toggleSelection(true);
            });
        }
    }
}
