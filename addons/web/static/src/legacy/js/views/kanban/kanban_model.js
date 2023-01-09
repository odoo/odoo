odoo.define('web.KanbanModel', function (require) {
"use strict";

/**
 * The KanbanModel extends the BasicModel to add Kanban specific features like
 * moving a record from a group to another, resequencing records...
 */

var BasicModel = require('web.BasicModel');
var viewUtils = require('web.viewUtils');

var KanbanModel = BasicModel.extend({
    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Adds a record to a group in the localData, and fetch the record.
     *
     * @param {string} groupID localID of the group
     * @param {integer} resId id of the record
     * @returns {Promise<string>} resolves to the local id of the new record
     */
    addRecordToGroup: function (groupID, resId) {
        var self = this;
        var group = this.localData[groupID];
        var new_record = this._makeDataPoint({
            res_id: resId,
            modelName: group.model,
            fields: group.fields,
            fieldsInfo: group.fieldsInfo,
            viewType: group.viewType,
            parentID: groupID,
        });

        var def = this._fetchRecord(new_record).then(function (result) {
            group.data.unshift(new_record.id);
            group.res_ids.unshift(resId);
            group.count++;

            // update the res_ids and count of the parent
            self.localData[group.parentID].count++;
            self._updateParentResIDs(group);

            return result.id;
        });
        return this._reloadProgressBarGroupFromRecord(new_record.id, def);
    },
    /**
     * Creates a new group from a name (performs a name_create).
     *
     * @param {string} name
     * @param {string} parentID localID of the parent of the group
     * @returns {Promise<string>} resolves to the local id of the new group
     */
    createGroup: function (name, parentID) {
        var self = this;
        var parent = this.localData[parentID];
        var groupBy = parent.groupedBy[0];
        var groupByField = parent.fields[groupBy];
        if (!groupByField || groupByField.type !== 'many2one') {
            return Promise.reject(); // only supported when grouped on m2o
        }
        return this._rpc({
                model: groupByField.relation,
                method: 'name_create',
                args: [name],
                context: parent.context, // todo: combine with view context
            })
            .then(function (result) {
                const createGroupDataPoint = (model, parent) => {
                    const newGroup = model._makeDataPoint({
                        modelName: parent.model,
                        context: parent.context,
                        domain: parent.domain.concat([[groupBy, "=", result[0]]]),
                        fields: parent.fields,
                        fieldsInfo: parent.fieldsInfo,
                        isOpen: true,
                        limit: parent.limit,
                        parentID: parent.id,
                        openGroupByDefault: true,
                        orderedBy: parent.orderedBy,
                        value: result,
                        viewType: parent.viewType,
                    });
                    if (parent.progressBar) {
                        newGroup.progressBarValues = _.extend({
                            counts: {},
                        }, parent.progressBar);
                    }
                    return newGroup;
                };
                const newGroup = createGroupDataPoint(self, parent);
                parent.data.push(newGroup.id);
                if (self.isInSampleMode()) {
                    // in sample mode, create the new group in both models (main + sample)
                    const sampleParent = self.sampleModel.localData[parentID];
                    const newSampleGroup = createGroupDataPoint(self.sampleModel, sampleParent);
                    sampleParent.data.push(newSampleGroup.id);
                }
                return newGroup.id;
            });
    },
    /**
     * Creates a new record from the given value, and add it to the given group.
     *
     * @param {string} groupID
     * @param {Object} values
     * @returns {Promise} resolved with the local id of the created record
     */
    createRecordInGroup: function (groupID, values) {
        var self = this;
        var group = this.localData[groupID];
        var context = this._getContext(group);
        var parent = this.localData[group.parentID];
        var groupByField = viewUtils.getGroupByField(parent.groupedBy[0]);
        context['default_' + groupByField] = viewUtils.getGroupValue(group, parent.groupedBy[0]);
        var def;
        if (Object.keys(values).length === 1 && 'display_name' in values) {
            // only 'display_name is given, perform a 'name_create'
            def = this._rpc({
                    model: parent.model,
                    method: 'name_create',
                    args: [values.display_name],
                    context: context,
                }).then(function (records) {
                    return records[0];
                });
        } else {
            // other fields are specified, perform a classical 'create'
            def = this._rpc({
                model: parent.model,
                method: 'create',
                args: [values],
                context: context,
            });
        }
        return def.then(function (resID) {
            return self.addRecordToGroup(group.id, resID);
        });
    },
    /**
     * Add the following (kanban specific) keys when performing a `get`:
     *
     * - tooltipData
     * - isGroupedByM2ONoColumn
     * - progressBarValues
     * - loadMoreCount
     * - loadMoreOffset
     *
     * @override
     * @see _readTooltipFields
     * @returns {Object}
     */
    __get: function () {
        var result = this._super.apply(this, arguments);
        var dp = result && this.localData[result.id];
        if (dp) {
            // Add tooltipData key
            if (dp.tooltipData) {
                result.tooltipData = $.extend(true, {}, dp.tooltipData);
            }
            // Add isGroupedByM2ONoColumn key
            if (dp.fields[dp.groupedBy[0]]) {
                var groupedByM2O = dp.fields[dp.groupedBy[0]].type === 'many2one';
                result.isGroupedByM2ONoColumn = !dp.data.length && groupedByM2O;
            } else {
                result.isGroupedByM2ONoColumn = false;
            }
            // Keep activeFilter
            result.activeFilter = dp.activeFilter;
            // Add progressBarValues, loadMoreCount and loadMoreOffset key
            let loadMoreCount = result.count - result.data.length;
            let loadMoreOffset = result.data.length;
            if (dp.progressBarValues) {
                result.progressBarValues = $.extend(true, {}, dp.progressBarValues);
                if (dp.activeFilter && dp.activeFilter.value) {
                    // A progressbar filter is in an activated state?
                    // Then set loadMoreCount and loadMoreOffset accordingly.
                    // These computations are needed because there might be
                    // records that doesn't match the current filter, e.g.:
                    // - newly created records
                    // - records dragged in the column
                    const barValues = dp.progressBarValues;
                    const barField = barValues.field;
                    const definedBarFieldValues = Object.keys(barValues.colors);
                    const filterValue = dp.activeFilter.value;

                    const filteredRecordsTotal = barValues.counts[filterValue];
                    const filteredRecords = result.data.filter(element => {
                        const elementBarFieldValue = element.data[barField];
                        return (filterValue === elementBarFieldValue)
                            || (filterValue === '__false'
                                && !definedBarFieldValues.includes(elementBarFieldValue));
                    });
                    loadMoreCount = filteredRecordsTotal - filteredRecords.length;
                    loadMoreOffset = filteredRecords.length;
                }
            }
            result.loadMoreCount = loadMoreCount;
            result.loadMoreOffset = loadMoreOffset;
        }
        return result;
    },
    /**
     * Same as @see get but getting the parent element whose ID is given.
     *
     * @param {string} id
     * @returns {Object}
     */
    getColumn: function (id) {
        var element = this.localData[id];
        if (element) {
            return this.get(element.parentID);
        }
        return null;
    },
    /**
     * @override
     */
    __load: function (params) {
        this.defaultGroupedBy = params.groupBy || [];
        params.groupedBy = (params.groupedBy && params.groupedBy.length) ? params.groupedBy : this.defaultGroupedBy;
        return this._super(params);
    },
    /**
     * Moves a record from a group to another.
     *
     * @param {string} recordID localID of the record
     * @param {string} groupID localID of the new group of the record
     * @param {string} parentID localID of the parent
     * @returns {Promise<string[]>} resolves to a pair [oldGroupID, newGroupID]
     */
    moveRecord: function (recordID, groupID, parentID) {
        var self = this;
        var parent = this.localData[parentID];
        var new_group = this.localData[groupID];
        var changes = {};
        var groupedFieldName = viewUtils.getGroupByField(parent.groupedBy[0]);
        var groupedField = parent.fields[groupedFieldName];
        // for a date/datetime field, we take the last moment of the group as the group value
        if (['date', 'datetime'].includes(groupedField.type)) {
            changes[groupedFieldName] = viewUtils.getGroupValue(new_group, parent.groupedBy[0]);
        } else if (groupedField.type === 'many2one') {
            changes[groupedFieldName] = {
                id: new_group.res_id,
                display_name: new_group.value,
            };
        } else if (groupedField.type === 'selection') {
            var value = _.findWhere(groupedField.selection, {1: new_group.value});
            changes[groupedFieldName] = value && value[0] || false;
        } else {
            changes[groupedFieldName] = new_group.value;
        }

        // Manually updates groups data. Note: this is done before the actual
        // save as it might need to perform a read group in some cases so those
        // updated data might be overridden again.
        var record = self.localData[recordID];
        var resID = record.res_id;
        // Remove record from its current group
        var old_group;
        for (var i = 0; i < parent.data.length; i++) {
            old_group = self.localData[parent.data[i]];
            var index = _.indexOf(old_group.data, recordID);
            if (index >= 0) {
                old_group.data.splice(index, 1);
                old_group.count--;
                if (!old_group.activeFilter || old_group.activeFilter.value === record.data[parent.progressBar.field]) {
                    // Here, the record leaving the old group matches its domain,
                    // so we must decrease the domainCount too.
                    old_group.domainCount--;
                }
                old_group.res_ids = _.without(old_group.res_ids, resID);
                self._updateParentResIDs(old_group);
                break;
            }
        }
        // Add record to its new group
        new_group.data.push(recordID);
        new_group.res_ids.push(resID);
        new_group.count++;

        return this.notifyChanges(recordID, changes).then(function () {
            return self.save(recordID);
        }).then(function () {
            record.parentID = new_group.id;
            return [old_group.id, new_group.id];
        });
    },
    /**
     * @override
     * @param {Object} options.activeFilter
     */
    reload: function (id, options) {
        const element = this.localData[id];
        // Reset the limit right before reloading a group as a reload
        // of a kanban view may update the limit of a group. @see BasicModel._readGroup()
        // (e.g. if we are coming back to the kanban view from a form view)
        // As this mechanism may only affect grouped kanban views, only reset
        // the limit if the current element is a group (and thus, has a parent).
        if (element.parentID) {
            element.limit = this.loadParams.limit;
        }
        // Register the domain extension in the element.
        if (options && options.activeFilter) {
            element.activeFilter = options.activeFilter || element.activeFilter;
            // Cleanup as this option is not used further
            delete options.activeFilter;
        }
        // if the groupBy is given in the options and if it is an empty array,
        // fallback on the default groupBy
        if (options && options.groupBy && !options.groupBy.length) {
            options.groupBy = this.defaultGroupedBy;
        }
        return this._super(id, options);
    },
    /**
     * @override
     */
    __reload: function (id, options) {
        var def = this._super(id, options);
        if (options && options.loadMoreOffset) {
            return def;
        }
        return this._reloadProgressBarGroupFromRecord(id, def);
    },
    /**
     * @override
     */
    save: function (recordID) {
        var def = this._super.apply(this, arguments);
        return this._reloadProgressBarGroupFromRecord(recordID, def);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _getGroupedListPropsToKeep(list, options) {
        const propsToKeep = this._super(...arguments);
        if (list.activeFilter) {
            propsToKeep.activeFilter = list.activeFilter;
        }
        return propsToKeep;
    },
    /**
     * @override
     */
    _getUngroupedListDomain(list) {
        const domainExtension = (list.activeFilter && list.activeFilter.domain) || [];
        return [...this._super(...arguments), ...domainExtension];
    },
    /**
     * @override
     */
    _makeDataPoint: function (params) {
        var dataPoint = this._super.apply(this, arguments);
        if (params.progressBar) {
            dataPoint.progressBar = params.progressBar;
        }
        // In Kanban view, we sometimes drag into a group records that are
        // outside of its domain. Here we make sure to remember the initial
        // domain count. This is useful for e.g. progressbars computations.
        dataPoint.domainCount = dataPoint.count;
        return dataPoint;
    },
    /**
     * @override
     */
    _load: function (dataPoint, options) {
        if (dataPoint.groupedBy.length && dataPoint.progressBar) {
            return this._readProgressBarGroup(dataPoint, options);
        }
        return this._super.apply(this, arguments);
    },
    /**
     * Ensures that there is no nested groups in Kanban (only the first grouping
     * level is taken into account).
     *
     * @override
     * @private
     * @param {Object} list valid resource object
     */
    _readGroup: function (list) {
        var self = this;
        if (list.groupedBy.length > 1) {
            list.groupedBy = [list.groupedBy[0]];
        }
        return this._super.apply(this, arguments).then(function (result) {
            return self._readTooltipFields(list).then(_.constant(result));
        });
    },
    /**
     * @private
     * @param {Object} dataPoint
     * @returns {Promise<Object>}
     */
    async _readProgressBarGroup(list, options) {
        const groupsDef = this._readGroup(list, options);
        const progressBarDef = this._readProgressBar(list);
        const [ /* groups */ , progressBar] = await Promise.all([groupsDef, progressBarDef]);

        // For each empty group having an active filter, we clear their filter and refetch.
        // For instance, this could arrive when we drag out all records of a column
        // having an active filter, or when the view domain has been updated.
        const groupProms = [];
        for (const groupId of list.data) {
            const group = this.localData[groupId];
            if (group.activeFilter && group.activeFilter.value && !group.data.length) {
                group.activeFilter = {};
                groupProms.push(this._fetchUngroupedList(group));
            }
        }
        await Promise.all(groupProms);

        // Compute records count for progressbar field values
        // not specified in the progressbar attributes
        for (const groupId of list.data) {
            const group = this.localData[groupId];
            const valuesCount = progressBar[group.value] || {};
            const valuesCountTotal = Object.keys(valuesCount).reduce((sum, key) => {
                return sum + valuesCount[key];
            }, 0);

            const counts = Object.assign({
                __false: group.domainCount - valuesCountTotal
            }, valuesCount);

            group.progressBarValues = Object.assign({
                counts,
            }, list.progressBar);
        }
        return list;
    },
    /**
     * @param {Object} list valid resource object
     * @returns {Promise}
     */
    _readProgressBar: function (list) {
        return this._rpc({
            model: list.model,
            method: 'read_progress_bar',
            kwargs: {
                domain: list.domain,
                group_by: list.groupedBy[0],
                progress_bar: list.progressBar,
                context: list.context,
            },
        });
    },
    /**
     * Fetches tooltip specific fields on the group by relation and stores it in
     * the column datapoint in a special key `tooltipData`.
     * Data for the tooltips (group_by_tooltip) are fetched in batch for all
     * groups, to avoid doing multiple calls.
     * Data are stored in a special key `tooltipData` on the datapoint.
     * Note that the option `group_by_tooltip` is only for m2o fields.
     *
     * @private
     * @param {Object} list a list of groups
     * @returns {Promise}
     */
    _readTooltipFields: function (list) {
        var self = this;
        var groupedByField = list.fields[list.groupedBy[0].split(':')[0]];
        if (groupedByField.type !== 'many2one') {
            return Promise.resolve();
        }
        var groupIds = _.reduce(list.data, function (groupIds, id) {
            var res_id = self.get(id, {raw: true}).res_id;
            // The field on which we are grouping might not be set on all records
            if (res_id) {
                groupIds.push(res_id);
            }
            return groupIds;
        }, []);
        var tooltipFields = [];
        var groupedByFieldInfo = list.fieldsInfo.kanban[list.groupedBy[0]];
        if (groupedByFieldInfo && groupedByFieldInfo.options) {
            tooltipFields = Object.keys(groupedByFieldInfo.options.group_by_tooltip || {});
        }
        if (groupIds.length && tooltipFields.length) {
            var fieldNames = _.union(['display_name'], tooltipFields);
            return this._rpc({
                model: groupedByField.relation,
                method: 'read',
                args: [groupIds, fieldNames],
                context: list.context,
            }).then(function (result) {
                _.each(list.data, function (id) {
                    var dp = self.localData[id];
                    dp.tooltipData = _.findWhere(result, {id: dp.res_id});
                });
            });
        }
        return Promise.resolve();
    },
    /**
     * Reloads all progressbar data. This is done after given promise and
     * ensures that the given promise's result is not lost.
     *
     * @private
     * @param {string} recordID
     * @param {Promise} def
     * @returns {Promise}
     */
   async  _reloadProgressBarGroupFromRecord(recordID, def) {
       let element = this.localData[recordID];
       if (element.type === 'list') {
           if (!element.parentID) {
               // we are reloading the whole view, so there is no need to manually
               // reload the progressbars
               return def;
           }
           if (element.activeFilter) {
               // We must not read_group when an active filter (and thus
               // a domain extension) is applied to the list datapoint.
               return def;
           }
       }
        // If we updated a record, then we must potentially update columns'
        // progressbars, so we need to load groups info again
        while (element) {
            if (element.progressBar) {
                const data = await def;
                await this._load(element, {
                    keepEmptyGroups: true,
                    onlyGroups: true,
                });
                return data;
            }
            element = this.localData[element.parentID];
        }
        return def;
    },
});
return KanbanModel;
});
