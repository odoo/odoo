/** @odoo-module alias=web.ListModel **/

    import BasicModel from 'web.BasicModel';

    var ListModel = BasicModel.extend({

        /**
         * @override
         * @param {Object} params.groupbys
         */
        init: function (parent, params) {
            this._super.apply(this, arguments);

            this.groupbys = params.groupbys;
        },

        //--------------------------------------------------------------------------
        // Public
        //--------------------------------------------------------------------------

        /**
         * overridden to add `groupData` when performing get on list datapoints.
         *
         * @override
         * @see _readGroupExtraFields
         */
        __get: function () {
            var result = this._super.apply(this, arguments);
            var dp = result && this.localData[result.id];
            if (dp && dp.groupData) {
                result.groupData = this.get(dp.groupData);
            }
            return result;
        },
        /**
         * For a list of records, performs a write with all changes and fetches
         * all data.
         *
         * @param {string} listDatapointId id of the parent list
         * @param {string} referenceRecordId the record datapoint used to
         *  generate the changes to apply to recordIds
         * @param {string[]} recordIds a list of record datapoint ids
         * @param {string} fieldName the field to write
         */
        saveRecords: function (listDatapointId, referenceRecordId, recordIds, fieldName) {
            var self = this;
            var referenceRecord = this.localData[referenceRecordId];
            var list = this.localData[listDatapointId];
            // generate all record values to ensure that we'll write something
            // (e.g. 2 records selected, edit a many2one in the first one, but
            // reset same value, we still want to save this value on the other
            // record)
            var allChanges = this._generateChanges(referenceRecord, {changesOnly: false});
            var changes = _.pick(allChanges, fieldName);
            var records = recordIds.map(function (recordId) {
                return self.localData[recordId];
            });
            var model = records[0].model;
            var recordResIds = _.pluck(records, 'res_id');
            var fieldNames = records[0].getFieldNames();
            var context = records[0].getContext();

            return this._rpc({
                model: model,
                method: 'write',
                args: [recordResIds, changes],
                context: context,
            }).then(function () {
                return self._rpc({
                    model: model,
                    method: 'read',
                    args: [recordResIds, fieldNames],
                    context: context,
                });
            }).then(function (results) {
                const updateLocalRecord = (id, data) => {
                    const record = self.localData[id];
                    record.data = _.extend({}, record.data, data);
                    record._changes = {};
                    record._isDirty = false;
                    self._parseServerData(fieldNames, record, record.data);
                };

                results.forEach(function (data) {
                    const record = _.findWhere(records, { res_id: data.id });
                    updateLocalRecord(record.id, data);

                    // Also update same resId records
                    self._updateDuplicateRecords(record.id, (id) => updateLocalRecord(id, data));
                });
            }).then(function () {
                if (!list.groupedBy.length) {
                    return Promise.all([
                        self._fetchX2ManysBatched(list),
                        self._fetchReferencesBatched(list)
                    ]);
                } else {
                    return Promise.all([
                        self._fetchX2ManysSingleBatch(list),
                        self._fetchReferencesSingleBatch(list)
                    ]);
                }
            });
        },

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         *
         * @override
         * @private
         */
        _readGroup: function (list, options) {
            var self = this;
            options = options || {};
            options.fetchRecordsWithGroups = true;
            return this._super(list, options).then(function (result) {
                return self._readGroupExtraFields(list).then(_.constant(result));
            });
        },
        /**
         * Fetches group specific fields on the group by relation and stores it
         * in the column datapoint in a special key `groupData`.
         * Data for the groups are fetched in batch for all groups, to avoid
         * doing multiple calls.
         * Note that the option is only for m2o fields.
         *
         * @private
         * @param {Object} list
         * @returns {Promise}
         */
        _readGroupExtraFields: function (list) {
            var self = this;
            var groupByFieldName = list.groupedBy[0].split(':')[0];
            var groupedByField = list.fields[groupByFieldName];
            if (groupedByField.type !== 'many2one' || !this.groupbys[groupByFieldName]) {
                return Promise.resolve();
            }
            var groupIds = _.reduce(list.data, function (groupIds, id) {
                var resId = self.get(id, { raw: true }).res_id;
                if (resId) { // the field might be undefined when grouping
                    groupIds.push(resId);
                }
                return groupIds;
            }, []);
            var groupFields = Object.keys(this.groupbys[groupByFieldName].viewFields);
            var prom;
            if (groupIds.length && groupFields.length) {
                prom = this._rpc({
                    model: groupedByField.relation,
                    method: 'read',
                    args: [groupIds, groupFields],
                    context: list.context,
                });
            }
            return Promise.resolve(prom).then(function (result) {
                var fvg = self.groupbys[groupByFieldName];
                _.each(list.data, function (id) {
                    var dp = self.localData[id];
                    var groupData = result && _.findWhere(result, {
                        id: dp.res_id,
                    });
                    var groupDp = self._makeDataPoint({
                        context: dp.context,
                        data: groupData,
                        fields: fvg.fields,
                        fieldsInfo: fvg.fieldsInfo,
                        modelName: groupedByField.relation,
                        parentID: dp.id,
                        res_id: dp.res_id,
                        viewType: 'groupby',
                    });
                    dp.groupData = groupDp.id;
                    self._parseServerData(groupFields, groupDp, groupDp.data);
                });
            });
        },
    });
    export default ListModel;
