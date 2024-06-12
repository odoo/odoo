/* @odoo-module */

import { DynamicList } from "./dynamic_list";

export class DynamicRecordList extends DynamicList {
    static type = "DynamicRecordList";

    /**
     * @param {import("./relational_model").Config} config
     * @param {Object} data
     */
    setup(config, data) {
        super.setup(config);
        this._setData(data);
    }

    _setData(data) {
        /** @type {import("./record").Record[]} */
        this.records = data.records.map((r) => this._createRecordDatapoint(r));
        this._updateCount(data);
    }

    // -------------------------------------------------------------------------
    // Getter
    // -------------------------------------------------------------------------

    get hasData() {
        return this.count > 0;
    }

    // -------------------------------------------------------------------------
    // Public
    // -------------------------------------------------------------------------

    /**
     * @param {number} resId
     * @param {boolean} [atFirstPosition]
     * @returns {Promise<Record>} the newly created record
     */
    addExistingRecord(resId, atFirstPosition) {
        return this.model.mutex.exec(async () => {
            const record = this._createRecordDatapoint({});
            await record._load({ resId });
            this._addRecord(record, atFirstPosition ? 0 : this.records.length);
            return record;
        });
    }

    /**
     * @param {boolean} [atFirstPosition=false]
     * @returns {Promise<Record>}
     */
    addNewRecord(atFirstPosition = false) {
        return this.model.mutex.exec(async () => {
            await this._leaveSampleMode();
            return this._addNewRecord(atFirstPosition);
        });
    }

    /**
     * Performs a search_count with the current domain to set the count. This is
     * useful as web_search_read limits the count for performance reasons, so it
     * might sometimes be less than the real number of records matching the domain.
     **/
    async fetchCount() {
        this.count = await this.model._updateCount(this.config);
        this.hasLimitedCount = false;
        return this.count;
    }

    moveRecord(dataRecordId, _dataGroupId, refId, _targetGroupId) {
        return this.resequence(dataRecordId, refId);
    }

    removeRecord(record) {
        if (!record.isNew) {
            throw new Error("removeRecord can't be called on an existing record");
        }
        const index = this.records.findIndex((r) => r === record);
        if (index < 0) {
            return;
        }
        this.records.splice(index, 1);
        this.count--;
        return record;
    }

    async resequence(movedRecordId, targetRecordId) {
        return this.model.mutex.exec(
            async () =>
                await this._resequence(this.records, this.resModel, movedRecordId, targetRecordId)
        );
    }

    // -------------------------------------------------------------------------
    // Protected
    // -------------------------------------------------------------------------

    async _addNewRecord(atFirstPosition) {
        const values = await this.model._loadNewRecord({
            resModel: this.resModel,
            activeFields: this.activeFields,
            fields: this.fields,
            context: this.context,
        });
        const record = this._createRecordDatapoint(values, "edit");
        this._addRecord(record, atFirstPosition ? 0 : this.records.length);
        return record;
    }

    _addRecord(record, index) {
        this.records.splice(Number.isInteger(index) ? index : this.records.length, 0, record);
        this.count++;
    }

    _createRecordDatapoint(data, mode = "readonly") {
        return new this.model.constructor.Record(
            this.model,
            {
                context: this.context,
                activeFields: this.activeFields,
                resModel: this.resModel,
                fields: this.fields,
                resId: data.id || false,
                resIds: data.id ? [data.id] : [],
                isMonoRecord: true,
                currentCompanyId: this.currentCompanyId,
                mode,
            },
            data,
            { manuallyAdded: !data.id }
        );
    }

    _getDPresId(record) {
        return record.resId;
    }

    _getDPFieldValue(record, handleField) {
        return record.data[handleField];
    }

    async _load(offset, limit, orderBy, domain) {
        await this.model._updateConfig(
            this.config,
            { offset, limit, orderBy, domain },
            { commit: this._setData.bind(this) }
        );
    }

    _removeRecords(recordIds) {
        const _records = this.records.filter((r) => !recordIds.includes(r.id));
        if (this.offset && !_records.length) {
            // we weren't on the first page, and we removed all records of the current page
            const offset = Math.max(this.offset - this.limit, 0);
            return this._load(offset, this.limit, this.orderBy, this.domain);
        }
        const nbRemovedRecords = this.records.length - _records.length;
        if (nbRemovedRecords > 0) {
            if (this.count > this.offset + this.limit) {
                // we removed some records, and there are other pages after the current one
                return this._load(this.offset, this.limit, this.orderBy, this.domain);
            } else {
                // we are on the last page and there are still records remaining
                this.count -= nbRemovedRecords;
                this.records = _records;
            }
        }
    }

    _updateCount(data) {
        const length = data.length;
        if (length >= this.config.countLimit + 1) {
            this.hasLimitedCount = true;
            this.count = this.config.countLimit;
        } else {
            this.hasLimitedCount = false;
            this.count = length;
        }
    }
}
