import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { DataPoint } from "./datapoint";
import { Record } from "./record";
import { resequence } from "./utils";

const DEFAULT_HANDLE_FIELD = "sequence";

export class DynamicList extends DataPoint {
    /**
     * @param {import("./relational_model").Config} config
     */
    setup(config) {
        super.setup(...arguments);
        this.handleField = Object.keys(this.activeFields).find(
            (fieldName) => this.activeFields[fieldName].isHandle
        );
        if (!this.handleField && DEFAULT_HANDLE_FIELD in this.fields) {
            this.handleField = DEFAULT_HANDLE_FIELD;
        }
        this.isDomainSelected = false;
        this.evalContext = { ...this.context, companies: this.config.companies };
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
        return resIds;
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
                if (!this.model._urgentSave) {
                    await editedRecord.checkValidity();
                    editedRecord = this.editedRecord;
                    if (!editedRecord) {
                        return true;
                    }
                }
                if (editedRecord.isNew && !editedRecord.dirty) {
                    this._removeRecords([editedRecord.id]);
                } else {
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

    async multiSave(record) {
        return this.model.mutex.exec(() => this._multiSave(record));
    }

    selectDomain(value) {
        return this.model.mutex.exec(() => this._selectDomain(value));
    }

    sortBy(fieldName) {
        return this.model.mutex.exec(() => {
            let orderBy = [...this.orderBy];
            if (orderBy.length && orderBy[0].name === fieldName) {
                orderBy[0] = { name: orderBy[0].name, asc: !orderBy[0].asc };
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

    // -------------------------------------------------------------------------
    // Protected
    // -------------------------------------------------------------------------

    async _duplicateRecords(records) {
        let resIds;
        if (records.length) {
            resIds = records.map((r) => r.resId);
        } else {
            resIds = await this.getResIds(true);
        }

        const duplicated = await this.model.orm.call(this.resModel, "copy", [resIds], {
            context: this.context,
        });
        if (resIds.length > duplicated.length) {
            this.model.notification.add(_t("Some records could not be duplicated"), {
                title: _t("Warning"),
            });
        }
        return this.model.load();
    }

    async _deleteRecords(records) {
        let resIds;
        if (records.length) {
            resIds = records.map((r) => r.resId);
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
            this.model.notification.add(msg, { title: _t("Warning") });
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

    async _multiSave(record) {
        const changes = record._getChanges();
        if (!Object.keys(changes).length || record === this._recordToDiscard) {
            return;
        }
        const validSelection = this.selection.filter((record) =>
            Object.keys(changes).every((fieldName) => {
                if (record._isReadonly(fieldName)) {
                    return false;
                } else if (record._isRequired(fieldName) && !changes[fieldName]) {
                    return false;
                }
                return true;
            })
        );
        const canProceed = await this.model.hooks.onWillSaveMulti(record, changes, validSelection);
        if (canProceed === false) {
            return false;
        }
        if (validSelection.length === 0) {
            this.model.dialog.add(AlertDialog, {
                body: _t("No valid record to save"),
                confirm: () => this.leaveEditMode({ discard: true }),
                dismiss: () => this.leaveEditMode({ discard: true }),
            });
            return false;
        } else {
            const resIds = validSelection.map((r) => r.resId);
            const context = this.context;
            try {
                await this.model.orm.write(this.resModel, resIds, changes, { context });
            } catch (e) {
                record._discard();
                this.model._updateConfig(record.config, { mode: "readonly" }, { reload: false });
                throw e;
            }
            const records = await this.model._loadRecords({ ...this.config, resIds });
            for (const record of validSelection) {
                const serverValues = records.find((r) => r.id === record.resId);
                record._applyValues(serverValues);
                this.model._updateSimilarRecords(record, serverValues);
            }
            record._discard();
            this.model._updateConfig(record.config, { mode: "readonly" }, { reload: false });
        }
        this.model.hooks.onSavedMulti(validSelection);
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
        if (resequencedRecords) {
            for (const dpData of resequencedRecords) {
                const dp = originalList.find((d) => getResId(d) === dpData.id);
                if (dp instanceof Record) {
                    dp._applyValues(dpData);
                } else {
                    dp[handleField] = dpData[handleField];
                }
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
            this.model.notification.add(msg, { title: _t("Warning") });
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
