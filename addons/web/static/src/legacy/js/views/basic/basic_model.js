/** @odoo-module alias=web.BasicModel **/

/**
 * Basic Model
 *
 * This class contains all the logic necessary to communicate between the
 * python models and the web client. More specifically, its job is to give a
 * simple unified API to the rest of the web client (in particular, the views and
 * the field widgets) to query and modify actual records in db.
 *
 * From a high level perspective, BasicModel is essentially a hashmap with
 * integer keys and some data and metadata object as value.  Each object in this
 * hashmap represents a piece of data, and can be reloaded and modified by using
 * its id as key in many methods.
 *
 * Here is a description of what those data point look like:
 *   var dataPoint = {
 *      _cache: {Object|undefined}
 *      _changes: {Object|null},
 *      aggregateValues: {Object},
 *      context: {Object},
 *      count: {integer},
 *      data: {Object|Object[]},
 *      domain: {*[]},
 *      fields: {Object},
 *      fieldsInfo: {Object},
 *      getContext: {function},
 *      getDomain: {function},
 *      getFieldNames: {function},
 *      groupedBy: {string[]},
 *      id: {integer},
 *      isOpen: {boolean},
 *      loadMoreOffset: {integer},
 *      limit: {integer},
 *      model: {string},
 *      offset: {integer},
 *      openGroupByDefault: {boolean},
 *      orderedBy: {Object[]},
 *      orderedResIDs: {integer[]},
 *      parentID: {string},
 *      rawContext: {Object},
 *      relationField: {string},
 *      res_id: {integer|null},
 *      res_ids: {integer[]},
 *      specialData: {Object},
 *      _specialDataCache: {Object},
 *      static: {boolean},
 *      type: {string} 'record' | 'list'
 *      value: ?,
 *  };
 *
 * Notes:
 * - id: is totally unrelated to res_id.  id is a web client local concept
 * - res_id: if set to a number or a virtual id (a virtual id is a character
 *     string composed of an integer and has a dash and other information), it
 *     is an actual id for a record in the server database. If set to
 *    'virtual_' + number, it is a record not yet saved (so, in create mode).
 * - res_ids: if set, it represent the context in which the data point is actually
 *     used.  For example, a given record in a form view (opened from a list view)
 *     might have a res_id = 2 and res_ids = [1,2,3]
 * - offset: this is mainly used for pagination.  Useful when we need to load
 *     another page, then we can simply change the offset and reload.
 * - count is basically the number of records being manipulated.  We can't use
 *     res_ids, because we might have a very large number of records, or a
 *     domain, and the res_ids would be the current page, not the full set.
 * - model is the actual name of a (odoo) model, such as 'res.partner'
 * - fields contains the description of all the fields from the model.  Note that
 *     these properties might have been modified by a view (for example, with
 *     required=true.  So, the fields kind of depends of the context of the
 *     data point.
 * - field_names: list of some relevant field names (string).  Usually, it
 *     denotes the fields present in the view.  Only those fields should be
 *     loaded.
 * - _cache and _changes are private, they should not leak out of the basicModel
 *   and be used by anyone else.
 *
 * Commands:
 *   commands are the base commands for x2many (0 -> 6), but with a
 *   slight twist: each [0, _, values] command is augmented with a virtual id:
 *   it means that when the command is added in basicmodel, it generates an id
 *   looking like this: 'virtual_' + number, and uses this id to identify the
 *   element, so it can be edited later.
 */

import { intersection, sortBy, unique } from "@web/core/utils/arrays";
import { uniqueId } from "@web/core/utils/functions";
import { omit, pick } from "@web/core/utils/objects";
import { sprintf } from "@web/core/utils/strings";
import AbstractModel from "web.AbstractModel";
import concurrency from "web.concurrency";
import Context from "web.Context";
import core from "web.core";
import Domain from "web.Domain";
import session from "web.session";
import utils from "web.utils";
import viewUtils from "web.viewUtils";

var _t = core._t;

const SENTINEL = null;

// field types that can be aggregated in grouped views
const AGGREGATABLE_TYPES = ['float', 'integer', 'monetary'];

var x2ManyCommands = {
    // (0, virtualID, {values})
    CREATE: 0,
    create: function (virtualID, values) {
        delete values.id;
        return [x2ManyCommands.CREATE, virtualID || false, values];
    },
    // (1, id, {values})
    UPDATE: 1,
    update: function (id, values) {
        delete values.id;
        return [x2ManyCommands.UPDATE, id, values];
    },
    // (2, id[, _])
    DELETE: 2,
    delete: function (id) {
        return [x2ManyCommands.DELETE, id, false];
    },
    // (3, id[, _]) removes relation, but not linked record itself
    FORGET: 3,
    forget: function (id) {
        return [x2ManyCommands.FORGET, id, false];
    },
    // (4, id[, _])
    LINK_TO: 4,
    link_to: function (id) {
        return [x2ManyCommands.LINK_TO, id, false];
    },
    // (5[, _[, _]])
    DELETE_ALL: 5,
    delete_all: function () {
        return [5, false, false];
    },
    // (6, _, ids) replaces all linked records with provided ids
    REPLACE_WITH: 6,
    replace_with: function (ids) {
        return [6, false, ids];
    }
};

var BasicModel = AbstractModel.extend({
    // constants
    OPEN_GROUP_LIMIT: 10, // after this limit, groups are automatically folded

    /**
     * @override
     */
    init: function () {
        // this mutex is necessary to make sure some operations are done
        // sequentially, for example, an onchange needs to be completed before a
        // save is performed.
        this.mutex = new concurrency.Mutex();
        this.bypassMutex = false; // never set this to true manually (see @executeDirectly)

        // this array is used to accumulate RPC requests done in the same call
        // stack, so that they can be batched in the minimum number of RPCs
        this.batchedRPCsRequests = [];

        this.localData = Object.create(null);
        // used to generate dataPoint ids. Note that the counter is set to 0 for
        // each instance, and this is mandatory for the sample data feature to
        // work: we need both the main model and the sample model to generate the
        // same datapoint ids for their common data (groups, when there are real
        // groups in database), so that we can easily do the mapping between
        // real and sample data.
        this.__id = 0;
        this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Add a default record to a list object. This method actually makes a new
     * record with the _makeDefaultRecord method, then adds it to the list object.
     * The default record is added in the data directly. This is meant to be used
     * by list or kanban controllers (i.e. not for x2manys in form views, as in
     * this case, we store changes as commands).
     *
     * @param {string} listID a valid handle for a list object
     * @param {Object} [options]
     * @param {string} [options.position=top] if the new record should be added
     *   on top or on bottom of the list
     * @returns {Promise<string>} resolves to the id of the new created record
     */
    addDefaultRecord: function (listID, options) {
        var self = this;
        var list = this.localData[listID];
        var context = Object.assign({}, this._getDefaultContext(list), this._getContext(list));

        var position = (options && options.position) || 'top';
        var params = {
            context: context,
            fields: list.fields,
            fieldsInfo: list.fieldsInfo,
            parentID: list.id,
            position: position,
            viewType: list.viewType,
        };
        return this._makeDefaultRecord(list.model, params).then(function (id) {
            list.count++;
            if (position === 'top') {
                list.data.unshift(id);
            } else {
                list.data.push(id);
            }
            var record = self.localData[id];
            list._cache[record.res_id] = id;
            return id;
        });
    },
    /**
     * Completes the fields and fieldsInfo of a dataPoint with the given ones.
     * It is useful for the cases where a record element is shared between
     * various views, such as a one2many with a tree and a form view.
     *
     * @param {string} datapointID a valid element ID (of type 'list' or 'record')
     * @param {Object} viewInfo
     * @param {Object} viewInfo.fields
     * @param {Object} viewInfo.fieldInfo
     * @param {string} viewInfo.viewType
     * @returns {Promise} resolved when the fieldInfo have been set on the given
     *   datapoint and all its children, and all rawChanges have been applied
     */
    addFieldsInfo: async function (dataPointID, viewInfo) {
        var dataPoint = this.localData[dataPointID];
        dataPoint.fields = Object.assign({}, dataPoint.fields, viewInfo.fields);
        // complete the given fieldInfo with the fields of the main view, so
        // that those field will be reloaded if a reload is triggered by the
        // secondary view
        dataPoint.fieldsInfo = dataPoint.fieldsInfo || {};
        const mainFieldInfo = dataPoint.fieldsInfo[dataPoint[viewInfo.viewType]];
        dataPoint.fieldsInfo[viewInfo.viewType] = Object.assign(
            {},
            mainFieldInfo,
            viewInfo.fieldInfo
        );

        // Some fields in the new fields info might not be in the previous one,
        // so we might have stored changes for them (e.g. coming from onchange
        // RPCs), that we haven't been able to process earlier (because those
        // fields were unknown at that time). So we now try to process them.
        if (dataPoint.type === 'record') {
            await this.applyRawChanges(dataPointID, viewInfo.viewType);
        }
            const proms = [];
            const fieldInfo = dataPoint.fieldsInfo[viewInfo.viewType];
            // recursively apply the new field info on sub datapoints
            if (dataPoint.type === 'list') {
                // case 'list': on all datapoints in the list
                Object.values(dataPoint._cache).forEach(subDataPointID => {
                    proms.push(this.addFieldsInfo(subDataPointID, {
                        fields: dataPoint.fields,
                        fieldInfo: dataPoint.fieldsInfo[viewInfo.viewType],
                        viewType: viewInfo.viewType,
                    }));
                });
            } else {
                // case 'record': on datapoints of all x2many fields
                const values = Object.assign({}, dataPoint.data, dataPoint._changes);
                Object.keys(fieldInfo).forEach(fieldName => {
                    const fieldType = dataPoint.fields[fieldName].type;
                    if (fieldType === 'one2many' || fieldType === 'many2many') {
                        const mode = fieldInfo[fieldName].mode;
                        const views = fieldInfo[fieldName].views;
                        const x2mDataPointID = values[fieldName];
                        if (views[mode] && x2mDataPointID) {
                            proms.push(this.addFieldsInfo(x2mDataPointID, {
                                fields: views[mode].fields,
                                fieldInfo: views[mode].fieldsInfo[mode],
                                viewType: mode,
                            }));
                        }
                    }
                });
            }
            return Promise.all(proms);
    },
    /**
     * Onchange RPCs may return values for fields that are not in the current
     * view. Those fields might even be unknown when the onchange returns (e.g.
     * in x2manys, we only know the fields that are used in the inner view, but
     * not those used in the potential form view opened in a dialog when a sub-
     * record is clicked). When this happens, we can't infer their type, so the
     * given value can't be processed. It is instead stored in the '_rawChanges'
     * key of the record, without any processing. Later on, if this record is
     * displayed in another view (e.g. the user clicked on it in the x2many
     * list, and the record opens in a dialog), those changes that were left
     * behind must be applied. This function applies changes stored in
     * '_rawChanges' for a given viewType.
     *
     * @param {string} recordID local resource id of a record
     * @param {string} viewType the current viewType
     * @returns {Promise<string>} resolves to the id of the record
     */
    applyRawChanges: function (recordID, viewType) {
        var record = this.localData[recordID];
        return this._applyOnChange(record._rawChanges, record, { viewType }).then(function () {
            return record.id;
        });
    },
    /**
     * Returns true if a record can be abandoned.
     *
     * Case for not abandoning the record:
     *
     * 1. flagged as 'no abandon' (i.e. during a `default_get`, including any
     *    `onchange` from a `default_get`)
     * 2. registered in a list on addition
     *
     *    2.1. registered as non-new addition
     *    2.2. registered as new additon on update
     *
     * 3. record is not new
     *
     * Otherwise, the record can be abandoned.
     *
     * This is useful when discarding changes on this record, as it means that
     * we must keep the record even if some fields are invalids (e.g. required
     * field is empty).
     *
     * @param {string} id id for a local resource
     * @returns {boolean}
     */
    canBeAbandoned: function (id) {
        // 1. no drop if flagged
        if (this.localData[id]._noAbandon) {
            return false;
        }
        // 2. no drop in a list on "ADD in some cases
        var record = this.localData[id];
        var parent = this.localData[record.parentID];
        if (parent) {
            var entry = parent._savePoint.find((p) => p.operation === "ADD" && p.id === id);
            if (entry) {
                // 2.1. no drop on non-new addition in list
                if (!entry.isNew) {
                    return false;
                }
                // 2.2. no drop on new addition on "UPDATE"
                var lastEntry = parent._savePoint.at(-1);
                if (lastEntry.operation === 'UPDATE' && lastEntry.id === id) {
                    return false;
                }
            }
        }
        // 3. drop new records
        return this.isNew(id);
    },
    /**
     * Delete a list of records, then, if the records have a parent, reload it.
     *
     * @todo we should remove the deleted records from the localData
     * @todo why can't we infer modelName? Because of grouped datapoint
     *       --> res_id doesn't correspond to the model and we don't have the
     *           information about the related model
     *
     * @param {string[]} recordIds list of local resources ids. They should all
     *   be of type 'record', be of the same model and have the same parent.
     * @param {string} modelName mode name used to unlink the records
     * @returns {Promise}
     */
    deleteRecords: function (recordIds, modelName) {
        var self = this;
        var records = recordIds.map((id) => self.localData[id]);
        var context = Object.assign(records[0].getContext(), session.user_context);
        return this._rpc({
                model: modelName,
                method: 'unlink',
                args: [records.map(r => r.res_id)],
                context: context,
            })
            .then(function () {
                records.forEach((record) => {
                    // discard any changes to prevent creating a new record with auto-save
                    self.discardChanges(record.id);
                    var parent = record.parentID && self.localData[record.parentID];
                    if (parent && parent.type === 'list') {
                        parent.data = parent.data.filter((x) => x !== record.id);
                        delete self.localData[record.id];
                        // Check if we are on last page and all records are deleted from current
                        // page i.e. if there is no state.data.length then go to previous page
                        if (!parent.data.length && parent.offset > 0) {
                            parent.offset = Math.max(parent.offset - parent.limit, 0);
                        }
                    } else {
                        record.res_ids.splice(record.offset, 1);
                        record.offset = Math.min(record.offset, record.res_ids.length - 1);
                        record.res_id = record.res_ids[record.offset];
                        record.count--;
                    }
                });
            });
    },
    /**
     * Discard all changes in a local resource.  Basically, it removes
     * everything that was stored in a _changes key.
     *
     * @param {string} id local resource id
     * @param {Object} [options]
     * @param {boolean} [options.rollback=false] if true, the changes will
     *   be reset to the last _savePoint, otherwise, they are reset to null
     */
    discardChanges: function (id, options) {
        options = options || {};
        var element = this.localData[id];
        var isNew = this.isNew(id);
        var rollback = 'rollback' in options ? options.rollback : isNew;
        var initialOffset = element.offset;
        element._domains = {};
        this._visitChildren(element, function (elem) {
            if (rollback && elem._savePoint) {
                if (elem._savePoint instanceof Array) {
                    elem._changes = elem._savePoint.slice(0);
                } else {
                    elem._changes = Object.assign({}, elem._savePoint);
                }
                elem._isDirty = !isNew;
            } else {
                elem._changes = null;
                elem._isDirty = false;
            }
            elem.offset = 0;
            if (elem.tempLimitIncrement) {
                elem.limit -= elem.tempLimitIncrement;
                delete elem.tempLimitIncrement;
            }
            elem.specialData = Object.assign({}, elem._specialDataSavepoint);
        });
        element.offset = initialOffset;
    },
    /**
     * Duplicate a record (by calling the 'copy' route)
     *
     * @param {string} recordID id for a local resource
     * @returns {Promise<string>} resolves to the id of duplicate record
     */
    duplicateRecord: function (recordID) {
        var self = this;
        var record = this.localData[recordID];
        var context = this._getContext(record);
        return this._rpc({
                model: record.model,
                method: 'copy',
                args: [record.data.id],
                context: context,
            })
            .then(function (res_id) {
                var index = record.res_ids.indexOf(record.res_id);
                record.res_ids.splice(index + 1, 0, res_id);
                return self.load({
                    fieldsInfo: record.fieldsInfo,
                    fields: record.fields,
                    modelName: record.model,
                    res_id: res_id,
                    res_ids: record.res_ids.slice(0),
                    viewType: record.viewType,
                    context: context,
                });
            });
    },
    /**
     * This method allows to execute a callback for which '_notifyChanges' and
     * 'save' will bypass the mutex. This is useful when we are leaving Odoo
     * (closing tab/browser), and we want to quickly save pending changes (in
     * an 'onbeforeunload' handler, which is mostly sync).
     *
     * This function should never be called except when we are leaving Odoo.
     *
     * @param {Function} callback
     */
    executeDirectly(callback) {
        this.bypassMutex = true;
        callback();
        this.bypassMutex = false;
    },
    /**
     * For list resources, this freezes the current records order.
     *
     * @param {string} listID a valid element ID of type list
     */
    freezeOrder: function (listID) {
        var list = this.localData[listID];
        if (list.type === 'record') {
            return;
        }
        list = this._applyX2ManyOperations(list);
        this._sortList(list);
        this.localData[listID].orderedResIDs = list.res_ids;
    },
    /**
     * The __get method first argument is the handle returned by the load method.
     * It is optional (the handle can be undefined).  In some case, it makes
     * sense to use the handle as a key, for example the BasicModel holds the
     * data for various records, each with its local ID.
     *
     * synchronous method, it assumes that the resource has already been loaded.
     *
     * @param {string} id local id for the resource
     * @param {any} options
     * @param {boolean} [options.env=false] if true, will only  return res_id
     *   (if record) or res_ids (if list)
     * @param {boolean} [options.raw=false] if true, will not follow relations
     * @returns {Object}
     */
    __get: function (id, options) {
        var self = this;
        options = options || {};

        if (!(id in this.localData)) {
            return null;
        }

        var element = this.localData[id];

        if (options.env) {
            var env = {
                ids: element.res_ids ? element.res_ids.slice(0) : [],
            };
            if (element.type === 'record') {
                env.currentId = this.isNew(element.id) ? undefined : element.res_id;
            }
            return env;
        }

        if (element.type === 'record') {
            var data = Object.assign({}, element.data, element._changes);
            var relDataPoint;
            for (var fieldName in data) {
                var field = element.fields[fieldName];
                if (data[fieldName] === null) {
                    data[fieldName] = false;
                }
                if (!field) {
                    continue;
                }

                // get relational datapoint
                if (field.type === 'many2one') {
                    if (options.raw) {
                        relDataPoint = this.localData[data[fieldName]];
                        data[fieldName] = relDataPoint ? relDataPoint.res_id : false;
                    } else {
                        data[fieldName] = this.__get(data[fieldName]) || false;
                    }
                } else if (field.type === 'reference') {
                    if (options.raw) {
                        relDataPoint = this.localData[data[fieldName]];
                        data[fieldName] = relDataPoint ?
                            relDataPoint.model + ',' + relDataPoint.res_id :
                            false;
                    } else {
                        data[fieldName] = this.__get(data[fieldName]) || false;
                    }
                } else if (field.type === 'one2many' || field.type === 'many2many') {
                    if (options.raw) {
                        if (typeof data[fieldName] === 'string') {
                            relDataPoint = this.localData[data[fieldName]];
                            relDataPoint = this._applyX2ManyOperations(relDataPoint);
                            data[fieldName] = relDataPoint.res_ids;
                        } else {
                            // no datapoint has been created yet (because the loading of relational
                            // data has been batched, and hasn't started yet), so the value is still
                            // the list of ids in the relation
                            data[fieldName] = data[fieldName] || [];
                        }
                    } else {
                        data[fieldName] = this.__get(data[fieldName]) || [];
                    }
                }
            }
            var record = {
                context: Object.assign({}, element.context),
                count: element.count,
                data: data,
                domain: element.domain.slice(0),
                evalModifiers: element.evalModifiers,
                fields: element.fields,
                fieldsInfo: element.fieldsInfo,
                getContext: element.getContext,
                getDomain: element.getDomain,
                getFieldNames: element.getFieldNames,
                id: element.id,
                isDirty: element.isDirty,
                isNew: element.isNew,
                limit: element.limit,
                model: element.model,
                offset: element.offset,
                ref: element.ref,
                res_ids: element.res_ids.slice(0),
                specialData: Object.assign({}, element.specialData),
                type: 'record',
                viewType: element.viewType,
            };

            if (!this.isNew(element.id)) {
                record.res_id = element.res_id;
            }
            var evalContext;
            Object.defineProperty(record, 'evalContext', {
                get: function () {
                    evalContext = evalContext || self._getEvalContext(element);
                    return evalContext;
                },
            });
            return record;
        }

        // apply potential changes (only for x2many lists)
        element = this._applyX2ManyOperations(element);
        this._sortList(element);

        if (!element.orderedResIDs && element._changes) {
            element._changes.forEach((change) => {
                if (change.operation === 'ADD' && change.isNew) {
                    element.data = element.data.filter((x) => x !== change.id);
                    if (change.position === 'top') {
                        element.data.unshift(change.id);
                    } else {
                        element.data.push(change.id);
                    }
                }
            });
        }

        var list = {
            aggregateValues: Object.assign({}, element.aggregateValues),
            context: Object.assign({}, element.context),
            count: element.count,
            data: element.data.map((elemID) => {
                return self.__get(elemID, options);
            }),
            domain: element.domain.slice(0),
            fields: element.fields,
            getContext: element.getContext,
            getDomain: element.getDomain,
            getFieldNames: element.getFieldNames,
            groupedBy: element.groupedBy,
            groupsCount: element.groupsCount,
            groupsLimit: element.groupsLimit,
            groupsOffset: element.groupsOffset,
            id: element.id,
            isDirty: element.isDirty,
            isM2MGrouped: element.isM2MGrouped,
            isNew: element.isNew,
            isOpen: element.isOpen,
            isSample: this.isSampleModel,
            limit: element.limit,
            model: element.model,
            offset: element.offset,
            orderedBy: element.orderedBy,
            res_id: element.res_id,
            res_ids: element.res_ids.slice(0),
            type: 'list',
            value: element.value,
            range: element.range,
            viewType: element.viewType,
        };
        if (element.fieldsInfo) {
            list.fieldsInfo = element.fieldsInfo;
        }
        return list;
    },
    /**
     * Generate default values for a given record. Those values are stored in
     * the '_changes' key of the record. For relational fields, sub-dataPoints
     * are created, and missing relational data is fetched.
     * Typically, this function is called when a new record is created. It may
     * also be called when a one2many subrecord is open in a form view (dialog),
     * to generate the default values for the fields displayed in the o2m form
     * view, but not in the list or kanban (mainly to correctly create
     * sub-dataPoints for relational fields).
     *
     * @param {string} recordID local id for a record
     * @param {Object} [options]
     * @param {string} [options.viewType] current viewType. If not set, we will
     *   assume main viewType from the record
     * @param {Array} [options.fieldNames] list of field names for which a
     *   default value must be generated (used to complete the values dict)
     * @returns {Promise}
     */
    generateDefaultValues(recordID, options = {}) {
        const record = this.localData[recordID];
        const viewType = options.viewType || record.viewType;
        const fieldNames = options.fieldNames || Object.keys(record.fieldsInfo[viewType]);
        const numericFields = ['float', 'integer', 'monetary'];
        const proms = [];
        record._changes = record._changes || {};
        fieldNames.forEach(fieldName => {
            record.data[fieldName] = null;
            if (!(fieldName in record._changes)) {
                const field = record.fields[fieldName];
                if (numericFields.includes(field.type)) {
                    record._changes[fieldName] = 0;
                } else if (field.type === 'one2many' || field.type === 'many2many') {
                    proms.push(this._processX2ManyCommands(record, fieldName, [], options));
                } else {
                    record._changes[fieldName] = null;
                }
            }
        });
        return Promise.all(proms);
    },
    /**
     * Returns the current display_name for the record.
     *
     * @param {string} id the localID for a valid record element
     * @returns {string}
     */
    getName: function (id) {
        var record = this.localData[id];
        var returnValue = '';
        if (record._changes && 'display_name' in record._changes) {
            returnValue = record._changes.display_name;
        }
        else if ('display_name' in record.data) {
            returnValue = record.data.display_name;
        }
        return returnValue || _t("New");
    },
    /**
     * Returns true if a record is dirty. A record is considered dirty if it has
     * some unsaved changes, marked by the _isDirty property on the record or
     * one of its subrecords.
     *
     * @param {string} id - the local resource id
     * @returns {boolean}
     */
    isDirty: function (id) {
        var isDirty = false;
        this._visitChildren(this.localData[id], function (r) {
            if (r._isDirty) {
                isDirty = true;
            }
        });
        return isDirty;
    },
    /**
     * Returns true iff the datapoint is of type list and either:
     *   - is not grouped, and contains no records
     *   - is grouped, and contains columns, but all columns are empty
     * In these cases, we will generate sample data to display, instead of an
     * empty state.
     *
     * @override
     */
    _isEmpty(dataPointID) {
        const dataPoint = this.localData[dataPointID];
        if (dataPoint.type === 'list') {
            const hasRecords = dataPoint.count === 0;
            if (dataPoint.groupedBy.length) {
                return dataPoint.data.length > 0 && hasRecords;
            } else {
                return hasRecords;
            }
        }
        return false;
    },
    /**
     * Check if a localData is new, meaning if it is in the process of being
     * created and no actual record exists in db. Note: if the localData is not
     * of the "record" type, then it is always considered as not new.
     *
     * Note: A virtual id is a character string composed of an integer and has
     * a dash and other information.
     * E.g: in calendar, the recursive event have virtual id linked to a real id
     * virtual event id "23-20170418020000" is linked to the event id 23
     *
     * @param {string} id id for a local resource
     * @returns {boolean}
     */
    isNew: function (id) {
        var data = this.localData[id];
        if (data.type !== "record") {
            return false;
        }
        var res_id = data.res_id;
        if (typeof res_id === 'number') {
            return false;
        } else if (typeof res_id === 'string' && /^[0-9]+-/.test(res_id)) {
            return false;
        }
        return true;
    },
    /**
     * Main entry point, the goal of this method is to fetch and process all
     * data (following relations if necessary) for a given record/list.
     *
     * @todo document all params
     *
     * @private
     * @param {any} params
     * @param {Object} [params.fieldsInfo={}] contains the fieldInfo of each field
     * @param {Object} params.fields contains the description of each field
     * @param {string} [params.type] 'record' or 'list'
     * @param {string} [params.recordID] an ID for an existing resource.
     * @returns {Promise<string>} resolves to a local id, or handle
     */
    __load: async function (params) {
        await this._super(...arguments);
        params.type = params.type || (params.res_id !== undefined ? 'record' : 'list');
        // FIXME: the following seems only to be used by the basic_model_tests
        // so it should probably be removed and the tests should be adapted
        params.viewType = params.viewType || 'default';
        if (!params.fieldsInfo) {
            var fieldsInfo = {};
            for (var fieldName in params.fieldNames) {
                fieldsInfo[params.fieldNames[fieldName]] = {};
            }
            params.fieldsInfo = {};
            params.fieldsInfo[params.viewType] = fieldsInfo;
        }

        if (params.type === 'record' && params.res_id === undefined) {
            params.allowWarning = true;
            return this._makeDefaultRecord(params.modelName, params);
        }
        var dataPoint = this._makeDataPoint(params);
        return this._load(dataPoint).then(function () {
            return dataPoint.id;
        });
    },
    /**
     * Returns the list of res_ids for a given list of local ids.
     *
     * @param {string[]} localIds
     * @returns {integer[]}
     */
    localIdsToResIds: function (localIds) {
        return localIds.map(localId => this.localData[localId].res_id);
    },
    /**
     * This helper method is designed to help developpers that want to use a
     * field widget outside of a view.  In that case, we want a way to create
     * data without actually performing a fetch.
     *
     * @param {string} model name of the model
     * @param {Object[]} fields a description of field properties
     * @param {Object} [fieldInfo] various field info that we want to set
     * @returns {Promise<string>} the local id for the created resource
     */
    makeRecord: function (model, fields, fieldInfo) {
        var self = this;
        var defs = [];
        var record_fields = {};
        fields.forEach((field) => {
            record_fields[field.name] = pick(field, 'type', 'relation', 'domain', 'selection');
        });
        fieldInfo = fieldInfo || {};
        var fieldsInfo = {};
        fieldsInfo.default = {};
        fields.forEach((field) => {
            fieldsInfo.default[field.name] = fieldInfo[field.name] || {};
        });
        var record = this._makeDataPoint({
            modelName: model,
            fields: record_fields,
            fieldsInfo: fieldsInfo,
            viewType: 'default',
        });
        fields.forEach((field) => {
            var dataPoint;
            record.data[field.name] = null;
            if (field.type === 'many2one') {
                if (field.value) {
                    var id = Array.isArray(field.value) ? field.value[0] : field.value;
                    var display_name = Array.isArray(field.value) ? field.value[1] : undefined;
                    dataPoint = self._makeDataPoint({
                        modelName: field.relation,
                        data: {
                            id: id,
                            display_name: display_name,
                        },
                        parentID: record.id,
                    });
                    record.data[field.name] = dataPoint.id;
                    if (display_name === undefined) {
                        defs.push(self._fetchNameGet(dataPoint));
                    }
                }
            } else if (field.type === 'reference' && field.value) {
                const ref = field.value.split(',');
                dataPoint = self._makeDataPoint({
                    context: record.context,
                    data: { id: parseInt(ref[1], 10) },
                    modelName: ref[0],
                    parentID: record.id,
                });
                defs.push(self._fetchNameGet(dataPoint));
                record.data[field.name] = dataPoint.id;
            } else if (field.type === 'one2many' || field.type === 'many2many') {
                var relatedFieldsInfo = {};
                relatedFieldsInfo.default = {};
                (field.fields || []).forEach((field) => {
                    relatedFieldsInfo.default[field.name] = {};
                });
                var dpParams = {
                    fieldsInfo: relatedFieldsInfo,
                    modelName: field.relation,
                    parentID: record.id,
                    static: true,
                    type: 'list',
                    viewType: 'default',
                };
                var needLoad = false;
                // As value, you could either pass:
                //  - a list of ids related to the record
                //  - a list of object
                // We only need to load the datapoint in the first case.
                if (field.value && field.value.length) {
                    if (typeof field.value[0] === "object") {
                        dpParams.res_ids = field.value.map((v) => v.id);
                        dataPoint = self._makeDataPoint(dpParams);
                        field.value.forEach((data) => {
                            var recordDP = self._makeDataPoint({
                                data: data,
                                modelName: field.relation,
                                parentID: dataPoint.id,
                                type: 'record',
                            });
                            dataPoint.data.push(recordDP.id);
                            dataPoint._cache[recordDP.res_id] = recordDP.id;
                        });
                    } else {
                        dpParams.res_ids = field.value;
                        dataPoint = self._makeDataPoint(dpParams);
                        needLoad = true;
                    }
                } else {
                    dpParams.res_ids = [];
                    dataPoint = self._makeDataPoint(dpParams);
                }

                if (needLoad) {
                    defs.push(self._load(dataPoint));
                }
                record.data[field.name] = dataPoint.id;
            } else if (field.value) {
                record.data[field.name] = field.value;
            }
        });
        return Promise.all(defs).then(function () {
            return record.id;
        });
    },
    /**
     * This is an extremely important method.  All changes in any field go
     * through this method.  It will then apply them in the local state, check
     * if onchanges needs to be applied, actually do them if necessary, then
     * resolves with the list of changed fields.
     *
     * @param {string} record_id
     * @param {Object} changes a map field => new value
     * @param {Object} [options] will be transferred to the applyChange method
     *   @see _applyChange
     * @returns {Promise<string[]>} list of changed fields
     */
    notifyChanges: function (record_id, changes, options) {
        const notifyChanges = () => this._applyChange(record_id, changes, options);
        if (this.bypassMutex) {
            return notifyChanges();
        }
        return this.mutex.exec(notifyChanges);
    },
    /**
     * Reload all data for a given resource. At any time there is at most one
     * reload operation active.
     *
     * @private
     * @param {string} id local id for a resource
     * @param {Object} [options]
     * @param {boolean} [options.keepChanges=false] if true, doesn't discard the
     *   changes on the record before reloading it
     * @returns {Promise<string>} resolves to the id of the resource
     */
    __reload: async function (id, options) {
        await this._super(...arguments);
        return this.mutex.exec(this._reload.bind(this, id, options));
    },
    /**
     * In some case, we may need to remove an element from a list, without going
     * through the notifyChanges machinery.  The motivation for this is when the
     * user click on 'Add a line' in a field one2many with a required field,
     * then clicks somewhere else.  The new line need to be discarded, but we
     * don't want to trigger a real notifyChanges (no need for that, and also,
     * we don't want to rerender the UI).
     *
     * @param {string} elementID some valid element id. It is necessary that the
     *   corresponding element has a parent.
     */
    removeLine: function (elementID) {
        var record = this.localData[elementID];
        var parent = this.localData[record.parentID];
        if (parent.static) {
            // x2Many case: the new record has been stored in _changes, as a
            // command so we remove the command(s) related to that record
            parent._changes = parent._changes.filter( change => {
                if (change.id === elementID &&
                    change.operation === 'ADD' && // For now, only an ADD command increases limits
                    parent.tempLimitIncrement) {
                        // The record will be deleted from the _changes.
                        // So we won't be passing into the logic of _applyX2ManyOperations anymore
                        // implying that we have to cancel out the effects of an ADD command here
                        parent.tempLimitIncrement--;
                        parent.limit--;
                }
                return change.id !== elementID;
            });
        } else {
            // main list view case: the new record is in data
            parent.data = parent.data.filter((x) => x !== elementID);
            parent.count--;
        }
    },
    /**
     * Resequences records.
     *
     * @param {string} modelName the resIDs model
     * @param {Array<integer>} resIDs the new sequence of ids
     * @param {string} parentID the localID of the parent
     * @param {object} [options]
     * @param {integer} [options.offset]
     * @param {string} [options.field] the field name used as sequence
     * @returns {Promise<string>} resolves to the local id of the parent
     */
    resequence: function (modelName, resIDs, parentID, options) {
        options = options || {};
        if ((resIDs.length <= 1)) {
            return Promise.resolve(parentID); // there is nothing to sort
        }
        var self = this;
        var data = this.localData[parentID];
        var params = {
            model: modelName,
            ids: resIDs,
            context: data.getContext(),
        };
        if (options.offset) {
            params.offset = options.offset;
        }
        if (options.field) {
            params.field = options.field;
        }
        return this._rpc({
                route: '/web/dataset/resequence',
                params: params,
            })
            .then(function (wasResequenced) {
                if (!wasResequenced) {
                    // the field on which the resequence was triggered does not
                    // exist, so no resequence happened server-side
                    return Promise.resolve();
                }
                var field = params.field ? params.field : 'sequence';

                return self._rpc({
                    model: modelName,
                    method: 'read',
                    args: [resIDs, [field]],
                    context: data.getContext(),
                }).then(function (records) {
                    if (data.data.length) {
                        var dataType = self.localData[data.data[0]].type;
                        if (dataType === 'record') {
                            data.data.forEach((dataPoint) => {
                                var recordData = self.localData[dataPoint].data;
                                var inRecords = records.find(({ id }) => id === recordData.id);
                                if (inRecords) {
                                    recordData[field] = inRecords[field];
                                }
                            });
                            data.data = sortBy(data.data, function (d) {
                                return self.localData[d].data[field];
                            });
                        }
                        if (dataType === 'list') {
                            data.data = sortBy(data.data, function (d) {
                                return resIDs.indexOf(self.localData[d].res_id);
                            });
                        }
                    }
                    data.res_ids = [];
                    data.data.forEach((d) => {
                        var dataPoint = self.localData[d];
                        if (dataPoint.type === 'record') {
                            data.res_ids.push(dataPoint.res_id);
                        } else {
                            data.res_ids = data.res_ids.concat(dataPoint.res_ids);
                        }
                    });
                    self._updateParentResIDs(data);
                    return parentID;
                })
            });
    },
    /**
     * Save a local resource, if needed.  This is a complicated operation,
     * - it needs to check all changes,
     * - generate commands for x2many fields,
     * - call the /create or /write method according to the record status
     * - After that, it has to reload all data, in case something changed, server side.
     *
     * @param {string} recordID local resource
     * @param {Object} [options]
     * @param {boolean} [options.reload=true] if true, data will be reloaded
     * @param {boolean} [options.savePoint=false] if true, the record will only
     *   be 'locally' saved: its changes written in a _savePoint key that can
     *   be restored later by call discardChanges with option rollback to true
     * @param {string} [options.viewType] current viewType. If not set, we will
     *   assume main viewType from the record
     * @returns {Promise}
     *   Resolved with the list of field names (whose value has been modified)
     */
    save: function (recordID, options) {
        var self = this;
        function _save() {
            options = options || {};
            var record = self.localData[recordID];
            if (options.savePoint) {
                self._visitChildren(record, function (rec) {
                    var newValue = rec._changes || rec.data;
                    if (newValue instanceof Array) {
                        rec._savePoint = newValue.slice(0);
                    } else {
                        rec._savePoint = Object.assign({}, newValue);
                    }
                });

                // save the viewType of edition, so that the correct readonly modifiers
                // can be evaluated when the record will be saved
                for (let fieldName in (record._changes || {})) {
                    record._editionViewType[fieldName] = options.viewType;
                }
            }
            var shouldReload = 'reload' in options ? options.reload : true;
            var method = self.isNew(recordID) ? 'create' : 'write';
            if (record._changes) {
                // id never changes, and should not be written
                delete record._changes.id;
            }
            var changes = self._generateChanges(record, {viewType: options.viewType, changesOnly: method !== 'create'});

            // id field should never be written/changed
            delete changes.id;

            if (method === 'create') {
                var fieldNames = record.getFieldNames();
                fieldNames.forEach((name) => {
                    if (changes[name] === null) {
                        delete changes[name];
                    }
                });
            }

            var prom = new Promise(function (resolve, reject) {
                var changedFields = Object.keys(changes);

                if (options.savePoint) {
                    resolve(changedFields);
                    return;
                }

                // in the case of a write, only perform the RPC if there are changes to save
                if (method === 'create' || changedFields.length) {
                    var args = method === 'write' ? [[record.data.id], changes] : [changes];
                    self._rpc({
                            model: record.model,
                            method: method,
                            args: args,
                            context: record.getContext(),
                        }).then(function (id) {
                            if (method === 'create') {
                                record.res_id = id;  // create returns an id, write returns a boolean
                                record.data.id = id;
                                record.offset = record.res_ids.length;
                                record.res_ids.push(id);
                                record.count++;
                            }

                            var _changes = record._changes;

                            // Erase changes as they have been applied
                            record._changes = {};
                            var data = Object.assign({}, record.data, record._changes);
                            for (var fieldName in record.fields) {
                                var type = record.fields[fieldName].type;
                                if (type === 'many2many' || type === 'one2many') {
                                    if (data[fieldName]) {
                                        self.localData[data[fieldName]]._changes = [];
                                    }
                                }
                            }

                            self.unfreezeOrder(record.id);

                            // Update the data directly or reload them
                            if (shouldReload) {
                                self._fetchRecord(record).then(
                                    function () {
                                        resolve(changedFields);
                                    },
                                    reject,
                                );
                            } else {
                                Object.assign(record.data, _changes);

                                record._changes = {};
                                for (const fieldName in record.fields) {
                                    if (['many2many', 'one2many'].includes(record.fields[fieldName].type) && record.data[fieldName]) {
                                        self.localData[record.data[fieldName]]._changes = [];
                                    }
                                }
                                resolve(changedFields);
                            }
                        }).guardedCatch(reject);
                        
                } else {
                    resolve(changedFields);
                }
            });
            prom.then(function () {
                self._updateDuplicateRecords(record.id, (id) => {
                    Object.assign(self.localData[id].data, record.data);
                });
                record._isDirty = false;
            });
            return prom;
        }
        if (this.bypassMutex) {
            return _save();
        } else {
            return this.mutex.exec(_save);
        }
    },
    /**
     * Manually sets a resource as dirty. This is used to notify that a field
     * has been modified, but with an invalid value. In that case, the value is
     * not sent to the basic model, but the record should still be flagged as
     * dirty so that it isn't discarded without any warning.
     *
     * @param {string} id a resource id
     */
    setDirty: function (id) {
        this.localData[id]._isDirty = true;
    },
    /**
     * For list resources, this changes the orderedBy key.
     *
     * @param {string} list_id id for the list resource
     * @param {string} fieldName valid field name
     * @returns {Promise}
     */
    setSort: function (list_id, fieldName) {
        var list = this.localData[list_id];
        if (list.type === 'record') {
            return;
        } else if (list._changes) {
            list._changes.forEach((change) => {
                delete change.isNew;
            });
        }
        if (list.orderedBy.length === 0) {
            list.orderedBy.push({name: fieldName, asc: true});
        } else if (list.orderedBy[0].name === fieldName){
            if (!list.orderedResIDs) {
                list.orderedBy[0].asc = !list.orderedBy[0].asc;
            }
        } else {
            var orderedBy = list.orderedBy.filter(o => o.name !== fieldName);
            list.orderedBy = [{name: fieldName, asc: true}].concat(orderedBy);
        }

        list.orderedResIDs = null;
        if (list.static) {
            // sorting might require to fetch the field for records where the
            // sort field is still unknown (i.e. on other pages for example)
            return this._fetchUngroupedList(list);
        }
        return Promise.resolve();
    },
    /**
     * For a given resource of type 'record', get the active field, if any.
     *
     * Since the ORM can support both `active` and `x_active` fields for
     * the archiving mechanism, check if any such field exists and prioritize
     * them. The `active` field should always take priority over its custom
     * version.
     *
     * @param {Object} record local resource
     * @returns {String|undefined} the field name to use for archiving purposes
     *   ('active', 'x_active') or undefined if no such field is present
     */
    getActiveField: function (record) {
        const fields = Object.keys(record.fields);
        const has_active = fields.includes('active');
        if (has_active) {
            return 'active';
        }
        const has_x_active = fields.includes('x_active');
        return has_x_active?'x_active':undefined
    },
    /**
     * Archive the given records
     *
     * @param {integer[]} resIDs ids of the records to archive
     * @param {string} parentID id of the parent resource to reload
     * @returns {Promise<string>} resolves to the parent id
     */
    actionArchive: function (resIDs, parentID) {
        var self = this;
        var parent = this.localData[parentID];
        return this._rpc({
                model: parent.model,
                method: 'action_archive',
                args: [resIDs],
            })
            .then(function (action) {
                if (Object.keys(action || {}).length > 0) {
                    return new Promise(function (resolve, reject) {
                        self.do_action(action, {
                            on_close: function (result) {
                                return self.trigger_up('reload', {
                                    onSuccess: resolve,
                                });
                            }
                        });
                    });
                } else {
                    return self.reload(parentID);
                }
            }).then(function (datapoint) {
                // if there are no records to display and we are not on first page(we check it
                // by checking offset is greater than limit i.e. we are not on first page)
                // reason for adding logic after reload to make sure there is no records after operation
                if (parent && parent.type === 'list' && !parent.data.length && parent.offset > 0) {
                    parent.offset = Math.max(parent.offset - parent.limit, 0);
                    return self.reload(parentID);
                }
                return datapoint;
            });
    },
    /**
     * Unarchive the given records
     *
     * @param {integer[]} resIDs ids of the records to unarchive
     * @param {string} parentID id of the parent resource to reload
     * @returns {Promise<string>} resolves to the parent id
     */
    actionUnarchive: function (resIDs, parentID) {
        var self = this;
        var parent = this.localData[parentID];
        return this._rpc({
                model: parent.model,
                method: 'action_unarchive',
                args: [resIDs],
            })
            .then(function (action) {
                // optionally clear the DataManager's cache
                if (Object.keys(action || {}).length > 0) {
                    return new Promise(function (resolve, reject) {
                        self.do_action(action, {
                            on_close: function () {
                                return self.trigger_up('reload', {
                                    onSuccess: resolve,
                                });
                            }
                        });
                    });
                } else {
                    return self.reload(parentID);
                }
            }).then(function (datapoint) {
                // if there are no records to display and we are not on first page(we check it
                // by checking offset is greater than limit i.e. we are not on first page)
                // reason for adding logic after reload to make sure there is no records after operation
                if (parent && parent.type === 'list' && !parent.data.length && parent.offset > 0) {
                    parent.offset = Math.max(parent.offset - parent.limit, 0);
                    return self.reload(parentID);
                }
                return datapoint;
            });
    },
    /**
     * Toggle (open/close) a group in a grouped list, then fetches relevant
     * data
     *
     * @param {string} groupId
     * @returns {Promise<string>} resolves to the group id
     */
    toggleGroup: function (groupId) {
        var self = this;
        var group = this.localData[groupId];
        if (group.isOpen) {
            group.isOpen = false;
            group.data = [];
            group.res_ids = [];
            group.offset = 0;
            this._updateParentResIDs(group);
            return Promise.resolve(groupId);
        }
        if (!group.isOpen) {
            group.isOpen = true;
            var def;
            if (group.count > 0) {
                def = this._load(group).then(function () {
                    self._updateParentResIDs(group);
                });
            }
            return Promise.resolve(def).then(function () {
                return groupId;
            });
        }
    },
    /**
     * For a list datapoint, unfreezes the current records order and sorts it.
     * For a record datapoint, unfreezes the x2many list datapoints.
     *
     * @param {string} elementID a valid element ID
     */
    unfreezeOrder: function (elementID) {
        var list = this.localData[elementID];
        if (list.type === 'record') {
            var data = Object.assign({}, list.data, list._changes);
            for (var fieldName in data) {
                var field = list.fields[fieldName];
                if (!field || !data[fieldName]) {
                    continue;
                }
                if (field.type === 'one2many' || field.type === 'many2many') {
                    var recordlist = this.localData[data[fieldName]];
                    recordlist.orderedResIDs = null;
                    for (var index in recordlist.data) {
                        this.unfreezeOrder(recordlist.data[index]);
                    }
                }
            }
            return;
        }
        list.orderedResIDs = null;
        this._sortList(list);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Add a default record to a list object. This method actually makes a new
     * record with the _makeDefaultRecord method, then adds it to the list object
     * as a 'ADD' command in its _changes. This is meant to be used x2many lists,
     * not by list or kanban controllers.
     *
     * @private
     * @param {Object} list a valid list object
     * @param {Object} [options]
     * @param {string} [options.position=top] if the new record should be added
     *   on top or on bottom of the list
     * @param {Array} [options.[context]] additional context to be merged before
     *   calling the default_get (eg. to set default values).
     *   If several contexts are found, multiple records are added
     * @param {boolean} [options.allowWarning=false] if true, the default record
     *   operation can complete, even if a warning is raised
     * @returns {Promise<[string]>} resolves to the new records ids
     */
    _addX2ManyDefaultRecord: function (list, options) {
        var self = this;
        var position = options && options.position || 'top';
        var params = {
            fields: list.fields,
            fieldsInfo: list.fieldsInfo,
            parentID: list.id,
            position: position,
            viewType: options.viewType || list.viewType,
            allowWarning: options && options.allowWarning
        };

        var additionalContexts = options && options.context;
        var makeDefaultRecords = [];
        if (additionalContexts){
            additionalContexts.forEach((context) => {
                params.context = self._getContext(list, {additionalContext: context, full: true, sanitize_default_values: true});
                makeDefaultRecords.push(self._makeDefaultRecord(list.model, params));
            });
        } else {
            params.context = self._getContext(list, {sanitize_default_values: true});
            makeDefaultRecords.push(self._makeDefaultRecord(list.model, params));
        }

        return Promise.all(makeDefaultRecords).then(function (resultIds){
            var ids = [];
            resultIds.forEach((id) => {
                ids.push(id);

                list._changes.push({operation: 'ADD', id: id, position: position, isNew: true});
                var record = self.localData[id];
                list._cache[record.res_id] = id;
                if (list.orderedResIDs) {
                    var index = list.offset + (position !== 'top' ? list.limit : 0);
                    list.orderedResIDs.splice(index, 0, record.res_id);
                    // list could be a copy of the original one
                    self.localData[list.id].orderedResIDs = list.orderedResIDs;
                }
            });

            return ids;
        });
    },
    /**
     * This method is the private version of notifyChanges.  Unlike
     * notifyChanges, it is not protected by a mutex.  Every changes from the
     * user to the model go through this method.
     *
     * @param {string} recordID
     * @param {Object} changes
     * @param {Object} [options]
     * @param {boolean} [options.doNotSetDirty=false] if this flag is set to
     *   true, then we will not tag the record as dirty.  This should be avoided
     *   for most situations.
     * @param {boolean} [options.notifyChange=true] if this flag is set to
     *   false, then we will not notify and not trigger the onchange, even though
     *   it was changed.
     * @param {string} [options.viewType] current viewType. If not set, we will assume
     *   main viewType from the record
     * @param {boolean} [options.allowWarning=false] if true, change
     *   operation can complete, even if a warning is raised
     *   (only supported by X2ManyChange)
     * @returns {Promise} list of changed fields
     */
    _applyChange: function (recordID, changes, options) {
        var self = this;
        var record = this.localData[recordID];
        var field;
        var defs = [];
        options = options || {};
        record._changes = record._changes || {};
        if (!options.doNotSetDirty) {
            record._isDirty = true;
        }
        var initialData = {};
        this._visitChildren(record, function (elem) {
            initialData[elem.id] = $.extend(true, {}, pick(elem, 'data', '_changes'));
        });

        // apply changes to local data
        for (var fieldName in changes) {
            field = record.fields[fieldName];
            if (field && (field.type === 'one2many' || field.type === 'many2many')) {
                defs.push(this._applyX2ManyChange(record, fieldName, changes[fieldName], options));
            } else if (field && (field.type === 'many2one' || field.type === 'reference')) {
                defs.push(this._applyX2OneChange(record, fieldName, changes[fieldName], options));
            } else {
                record._changes[fieldName] = changes[fieldName];
            }
        }

        if (options.notifyChange === false) {
            return Promise.all(defs).then(function () {
                return Promise.resolve(Object.keys(changes));
            });
        }

        return Promise.all(defs).then(function () {
            var onChangeFields = []; // the fields that have changed and that have an on_change
            for (var fieldName in changes) {
                field = record.fields[fieldName];
                if (field && field.onChange) {
                    var isX2Many = field.type === 'one2many' || field.type === 'many2many';
                    if (!isX2Many || (self._isX2ManyValid(record._changes[fieldName] || record.data[fieldName]))) {
                        onChangeFields.push(fieldName);
                    }
                }
            }
            return new Promise(function (resolve, reject) {
                if (onChangeFields.length) {
                    self._performOnChange(record, onChangeFields, { viewType: options.viewType })
                    .then(function (result) {
                        delete record._warning;
                        resolve(Object.keys(changes).concat(Object.keys(result && result.value || {})));
                    }).guardedCatch(function () {
                        self._visitChildren(record, function (elem) {
                            Object.assign(elem, initialData[elem.id]);
                        });
                        reject();
                    });
                } else {
                    resolve(Object.keys(changes));
                }
            }).then(function (fieldNames) {
                return self._fetchSpecialData(record).then(function (fieldNames2) {
                    // Return the names of the fields that changed (onchange or
                    // associated special data change)
                    return fieldNames.concat(fieldNames2);
                });
            });
        });
    },
    /**
     * Apply an x2one (either a many2one or a reference field) change. There is
     * a need for this function because the server only gives an id when a
     * onchange modifies a many2one field. For this reason, we need (sometimes)
     * to do a read of display_name.
     *
     * Moreover, for the many2one case, a new value can sometimes be set (i.e.
     * a display_name is given, but no id). When this happens, we first do a
     * name_create.
     *
     * @param {Object} record
     * @param {string} fieldName
     * @param {Object} [data]
     * @param {Object} [options]
     * @param {string} [options.viewType] current viewType. If not set, we will
     *   assume main viewType from the record
     * @returns {Promise}
     */
    _applyX2OneChange: async function (record, fieldName, data, options) {
        options = options || {};
        var self = this;
        if (!data || (!data.id && !data.display_name)) {
            record._changes[fieldName] = false;
            return Promise.resolve();
        }

        const field = record.fields[fieldName];
        const coModel = field.type === 'reference' ? data.model : field.relation;
        const allowedTypes = ['many2one', 'reference'];
        if (allowedTypes.includes(field.type) && !data.id && data.display_name) {
            // only display_name given -> do a name_create
            const result = await this._rpc({
                model: coModel,
                method: 'name_create',
                args: [data.display_name],
                context: this._getContext(record, {fieldName: fieldName, viewType: options.viewType}),
            });
            // Check if a record is really created. Models without defined
            // _rec_name cannot create record based on name_create.
            if (!result) {
                record._changes[fieldName] = false;
                return Promise.resolve();
            }
            data = {id: result[0], display_name: result[1]};
        }

        // here, we check that the many2one really changed. If the res_id is the
        // same, we do not need to do any extra work. It can happen when the
        // user edited a manyone (with the small form view button) with an
        // onchange.  In that case, the onchange is triggered, but the actual
        // value did not change.
        var relatedID;
        if (record._changes && fieldName in record._changes) {
            relatedID = record._changes[fieldName];
        } else {
            relatedID = record.data[fieldName];
        }
        var relatedRecord = this.localData[relatedID];
        if (relatedRecord && (data.id === this.localData[relatedID].res_id)) {
            return Promise.resolve();
        }
        var rel_data = pick(data, 'id', 'display_name');

        const viewType = options.viewType || record.viewType;
        const fieldInfo = record.fieldsInfo[viewType][fieldName] || {};
        const fieldOptions = fieldInfo.options || {};

        // the reference field doesn't store its co-model in its field metadata
        // but directly in the data (as the co-model isn't fixed)
        var def;
        if (rel_data.display_name === undefined || fieldOptions.always_reload) {
            // TODO: refactor this to use _fetchNameGet
            def = this._rpc({
                    model: coModel,
                    method: 'read',
                    args: [data.id, ['display_name']],
                    context: this._getContext(record, { fieldName, viewType }),
                })
                .then(function (result) {
                    rel_data.display_name = result[0]['display_name'];
                });
        }
        return Promise.resolve(def).then(function () {
            var rec = self._makeDataPoint({
                context: record.context,
                data: rel_data,
                fields: {},
                fieldsInfo: {},
                modelName: coModel,
                parentID: record.id,
            });
            record._changes[fieldName] = rec.id;
        });
    },
    /**
     * Applies the result of an onchange RPC on a record.
     *
     * @private
     * @param {Object} values the result of the onchange RPC (a mapping of
     *   fieldnames to their value)
     * @param {Object} record
     * @param {Object} [options={}]
     * @param {string} [options.viewType] current viewType. If not set, we will assume
     *   main viewType from the record
     * @param {string} [options.firstOnChange] set to true if this is the first
     *   onchange (if so, some initialization will need to be done)
     * @returns {Promise}
     */
    _applyOnChange: function (values, record, options = {}) {
        var self = this;
        var defs = [];
        var rec;
        const viewType = options.viewType || record.viewType;
        record._changes = record._changes || {};

        for (let name in (values || {})) {
            const val = values[name];
            var field = record.fields[name];
            if (!field) {
                // this field is unknown so we can't process it for now (it is not
                // in the current view anyway, otherwise it wouldn't be unknown.
                // we store its value without processing it, so that if we later
                // on switch to another view in which this field is displayed,
                // we could process it as we would know its type then.
                // use case: an onchange sends a create command for a one2many,
                // in the dict of values, there is a value for a field that is
                // not in the one2many list, but that is in the one2many form.
                record._rawChanges[name] = val;
                // LPE TODO 1 taskid-2261084: remove this entire comment including code snippet
                // when the change in behavior has been thoroughly tested.
                // It is impossible to distinguish between values returned by the default_get
                // and those returned by the onchange. Since those are not in _changes, they won't be saved.
                // if (options.firstOnChange) {
                //     record._changes[name] = val;
                // }
                continue;
            }
            if (record._rawChanges[name]) {
                // if previous _rawChanges exists, clear them since the field is now knwon
                // and restoring outdated onchange over posterious change is wrong
                delete record._rawChanges[name];
            }
            var oldValue = name in record._changes ? record._changes[name] : record.data[name];
            var id;
            if (field.type === 'many2one') {
                id = false;
                // in some case, the value returned by the onchange can
                // be false (no value), so we need to avoid creating a
                // local record for that.
                if (val) {
                    // when the value isn't false, it can be either
                    // an array [id, display_name] or just an id.
                    var data = Array.isArray(val) ?
                        {id: val[0], display_name: val[1]} :
                        {id: val};
                    if (!oldValue || (self.localData[oldValue].res_id !== data.id)) {
                        // only register a change if the value has changed
                        rec = self._makeDataPoint({
                            context: record.context,
                            data: data,
                            modelName: field.relation,
                            parentID: record.id,
                        });
                        id = rec.id;
                        record._changes[name] = id;
                    }
                } else if (oldValue !== false) {
                    // if no value is provided for a m2o,
                    // we should only consider the field updated if it had a value before
                    record._changes[name] = false;
                }
            } else if (field.type === 'reference') {
                id = false;
                if (val) {
                    var ref = val.split(',');
                    var modelName = ref[0];
                    var resID = parseInt(ref[1]);
                    if (!oldValue || self.localData[oldValue].res_id !== resID ||
                        self.localData[oldValue].model !== modelName) {
                        // only register a change if the value has changed
                        rec = self._makeDataPoint({
                            context: record.context,
                            data: {id: parseInt(ref[1])},
                            modelName: modelName,
                            parentID: record.id,
                        });
                        defs.push(self._fetchNameGet(rec));
                        id = rec.id;
                        record._changes[name] = id;
                    }
                } else {
                    record._changes[name] = id;
                }
            } else if (field.type === 'one2many' || field.type === 'many2many') {
                var listId = record._changes[name] || record.data[name];
                var list;
                if (listId) {
                    list = self.localData[listId];
                } else {
                    var fieldInfo = record.fieldsInfo[viewType][name];
                    if (!fieldInfo) {
                        // ignore changes of x2many not in view
                        continue;
                    }
                    var view = fieldInfo.views && fieldInfo.views[fieldInfo.mode];
                    list = self._makeDataPoint({
                        fields: view ? view.fields : fieldInfo.relatedFields,
                        fieldsInfo: view ? view.fieldsInfo : fieldInfo.fieldsInfo,
                        limit: fieldInfo.limit,
                        modelName: field.relation,
                        parentID: record.id,
                        static: true,
                        type: 'list',
                        viewType: view ? view.type : fieldInfo.viewType,
                    });
                }
                // TODO: before registering the changes, verify that the x2many
                // value has changed
                record._changes[name] = list.id;
                list._changes = list._changes || [];

                // save it in case of a [5] which will remove the _changes
                var oldChanges = list._changes;
                val.forEach((command) => {
                    var rec, recID;
                    if (command[0] === 0 || command[0] === 1) {
                        // CREATE or UPDATE
                        if (command[0] === 0 && command[1]) {
                            // updating an existing (virtual) record
                            var previousChange = oldChanges.find(operation => {
                                var child = self.localData[operation.id];
                                return child && (child.ref === command[1]);
                            });
                            recID = previousChange && previousChange.id;
                            rec = self.localData[recID];
                        }
                        if (command[0] === 1 && command[1]) {
                            // updating an existing record
                            rec = self.localData[list._cache[command[1]]];
                        }
                        if (!rec) {
                            var params = {
                                context: list.context,
                                fields: list.fields,
                                fieldsInfo: list.fieldsInfo,
                                modelName: list.model,
                                parentID: list.id,
                                viewType: list.viewType,
                                ref: command[1],
                            };
                            if (command[0] === 1) {
                                params.res_id = command[1];
                            }
                            rec = self._makeDataPoint(params);
                            list._cache[rec.res_id] = rec.id;
                            if (options.firstOnChange) {
                                // this is necessary so the fields are initialized
                                rec.getFieldNames().forEach(fieldName => {
                                    if (!(fieldName in rec.data)) {
                                        rec.data[fieldName] = null;
                                    }
                                });
                            }
                        }
                        // Do not abandon the record if it has been created
                        // from `default_get`. The list has a savepoint only
                        // after having fully executed `default_get`.
                        rec._noAbandon = !list._savePoint;
                        list._changes.push({operation: 'ADD', id: rec.id});
                        if (command[0] === 1) {
                            list._changes.push({operation: 'UPDATE', id: rec.id});
                        }
                        defs.push(self._applyOnChange(command[2], rec, {
                            firstOnChange: options.firstOnChange,
                        }));
                    } else if (command[0] === 4) {
                        // LINK TO
                        linkRecord(list, command[1]);
                    } else if (command[0] === 5) {
                        // DELETE ALL
                        list._changes = [{operation: 'REMOVE_ALL'}];
                    } else if (command[0] === 6) {
                        list._changes = [{operation: 'REMOVE_ALL'}];
                        Object.values(command[2] || {}).forEach((resID) => {
                            linkRecord(list, resID);
                        });
                    }
                });
                var def = self._readUngroupedList(list).then(function (list) {
                    var x2ManysDef = self._fetchX2ManysBatched(list);
                    var referencesDef = self._fetchReferencesBatched(list);
                    return Promise.all([x2ManysDef, referencesDef]);
                });
                defs.push(def);
            } else {
                var newValue = self._parseServerValue(field, val);
                if (newValue !== oldValue) {
                    record._changes[name] = newValue;
                }
            }
        }
        return Promise.all(defs);

        // inner function that adds a record (based on its res_id) to a list
        // dataPoint (used for onchanges that return commands 4 (LINK TO) or
        // commands 6 (REPLACE WITH))
        function linkRecord (list, resID) {
            rec = self.localData[list._cache[resID]];
            if (rec) {
                // modifications done on a record are discarded if the onchange
                // uses a LINK TO or a REPLACE WITH
                self.discardChanges(rec.id);
            }
            // the dataPoint id will be set when the record will be fetched (for
            // now, this dataPoint may not exist yet)
            list._changes.push({
                operation: 'ADD',
                id: rec ? rec.id : null,
                resID: resID,
            });
        }
    },
    /**
     * When an operation is applied to a x2many field, the field widgets
     * generate one (or more) command, which describes the exact operation.
     * This method tries to interpret these commands and apply them to the
     * localData.
     *
     * @param {Object} record
     * @param {string} fieldName
     * @param {Object} command A command object.  It should have a 'operation'
     *   key.  For example, it looks like {operation: ADD, id: 'partner_1'}
     * @param {Object} [options]
     * @param {string} [options.viewType] current viewType. If not set, we will assume
     *   main viewType from the record
     * @param {boolean} [options.allowWarning=false] if true, change
     *   operation can complete, even if a warning is raised
     *   (only supported by the 'CREATE' command.operation)
     * @returns {Promise}
     */
    _applyX2ManyChange: async function (record, fieldName, command, options) {
        if (command.operation === 'TRIGGER_ONCHANGE') {
            // the purpose of this operation is to trigger an onchange RPC, so
            // there is no need to apply any change on the record (the changes
            // have probably been already applied and saved, usecase: many2many
            // edition in a dialog)
            return Promise.resolve();
        }

        var self = this;
        var localID = (record._changes && record._changes[fieldName]) || record.data[fieldName];
        var list = this.localData[localID];
        var field = record.fields[fieldName];
        var viewType = (options && options.viewType) || record.viewType;
        var fieldInfo = record.fieldsInfo[viewType][fieldName];
        var view = fieldInfo.views && fieldInfo.views[fieldInfo.mode];
        var def, rec;
        var defs = [];
        list._changes = list._changes || [];

        switch (command.operation) {
            case 'ADD':
                // for now, we are in the context of a one2many field
                // the command should look like this:
                // { operation: 'ADD', id: localID }
                // The corresponding record may contain value for fields that
                // are unknown in the list (e.g. fields that are in the
                // subrecord form view but not in the kanban or list view), so
                // to ensure that onchanges are correctly handled, we extend the
                // list's fields with those in the created record
                var newRecord = this.localData[command.id];
                list.fields = Object.assign(newRecord.fields, list.fields);
                list.fieldsInfo = Object.assign(newRecord.fieldsInfo, list.fieldsInfo);
                newRecord.fields = list.fields;
                newRecord.fieldsInfo = list.fieldsInfo;
                newRecord.viewType = list.viewType;
                list._cache[newRecord.res_id] = newRecord.id;
                list._changes.push(command);
                break;
            case 'ADD_M2M':
                // force to use link command instead of create command
                list._forceM2MLink = true;
                // handle multiple add: command[2] may be a dict of values (1
                // record added) or an array of dict of values
                var data = Array.isArray(command.ids) ? command.ids : [command.ids];

                // name_create records for which there is no id (typically, could
                // be the case of a quick_create in a many2many_tags, so data.length
                // is 1)
                for (const r of data) {
                    if (!r.id && r.display_name) {
                        const prom = this._rpc({
                            model: field.relation,
                            method: 'name_create',
                            args: [r.display_name],
                            context: this._getContext(record, {fieldName: fieldName, viewType: options.viewType}),
                        }).then(result => {
                            r.id = result[0];
                            r.display_name = result[1];
                        });
                        defs.push(prom);
                    }
                }
                await Promise.all(defs);

                // Ensure the local data repository (list) boundaries can handle incoming records (data)
                if (data.length + list.res_ids.length > list.limit) {
                    list.limit = data.length + list.res_ids.length;
                }

                var list_records = {};
                data.forEach((d) => {
                    rec = self._makeDataPoint({
                        context: record.context,
                        modelName: field.relation,
                        fields: view ? view.fields : fieldInfo.relatedFields,
                        fieldsInfo: view ? view.fieldsInfo : fieldInfo.fieldsInfo,
                        res_id: d.id,
                        data: d,
                        viewType: view ? view.type : fieldInfo.viewType,
                        parentID: list.id,
                    });
                    list_records[d.id] = rec;
                    list._cache[rec.res_id] = rec.id;
                    list._changes.push({operation: 'ADD', id: rec.id});
                });
                // read list's records as we only have their ids and optionally their display_name
                // (we can't use function readUngroupedList because those records are only in the
                // _changes so this is a very specific case)
                // this could be optimized by registering the fetched records in the list's _cache
                // so that if a record is removed and then re-added, it won't be fetched twice
                var fieldNames = list.getFieldNames();
                if (fieldNames.length) {
                    def = this._rpc({
                        model: list.model,
                        method: 'read',
                        args: [data.map((d) => d.id), fieldNames],
                        context: Object.assign({}, record.context, field.context, list.getContext()),
                    }).then(function (records) {
                        records.forEach((record) => {
                            list_records[record.id].data = record;
                            self._parseServerData(fieldNames, list, record);
                        });
                        return Promise.all([
                            self._fetchX2ManysBatched(list),
                            self._fetchReferencesBatched(list)
                        ]);
                    });
                    defs.push(def);
                }
                break;
            case 'CREATE':
                var createOptions = Object.assign({
                    context: command.context,
                    position: command.position
                }, options || {});
                createOptions.viewType = fieldInfo.mode;

                def = this._addX2ManyDefaultRecord(list, createOptions).then(function (ids) {
                    ids.forEach((id) => {
                        if (command.position === 'bottom' && list.orderedResIDs && list.orderedResIDs.length >= list.limit) {
                            list.tempLimitIncrement = (list.tempLimitIncrement || 0) + 1;
                            list.limit += 1;
                        }
                        // FIXME: hack for lunch widget, which does useless default_get and onchange
                        if (command.data) {
                            return self._applyChange(id, command.data);
                        }
                    });
                });
                defs.push(def);
                break;
            case 'UPDATE':
                list._changes.push({operation: 'UPDATE', id: command.id});
                if (command.data) {
                    defs.push(this._applyChange(command.id, command.data, {
                        viewType: view && view.type,
                    }));
                }
                break;
            case 'FORGET':
                // Unlink the record of list.
                list._forceM2MUnlink = true;
            case 'DELETE':
                // filter out existing operations involving the current
                // dataPoint, and add a 'DELETE' or 'FORGET' operation only if there is
                // no 'ADD' operation for that dataPoint, as it would mean
                // that the record wasn't in the relation yet
                var idsToRemove = command.ids;

                list._changes = list._changes.filter(change => {
                    var idInCommands = command.ids.includes(change.id);
                    if (idInCommands && change.operation === 'ADD') {
                        idsToRemove = idsToRemove.filter(id => id !== change.id);
                    }
                    return !idInCommands;
                });
                idsToRemove.forEach(id => {
                    var operation = list._forceM2MUnlink ? 'FORGET': 'DELETE';
                    list._changes.push({operation: operation, id: id});
                });
                break;
            case 'DELETE_ALL':
                // first remove all pending 'ADD' operations
                list._changes = list._changes.filter(change => change.operation !== 'ADD');

                // then apply 'DELETE' on existing records
                return this._applyX2ManyChange(record, fieldName, {
                    operation: 'DELETE',
                    ids: list.res_ids
                }, options);
            case 'REPLACE_WITH':
                // this is certainly not optimal... and not sure that it is
                // correct if some ids are added and some other are removed
                list._changes = [];
                var newIds = command.ids.filter((x) => list.res_ids.indexOf(x) < 0);
                var removedIds = list.res_ids.filter((x) => command.ids.indexOf(x) < 0);
                var addDef, removedDef, values;
                if (newIds.length) {
                    values = newIds.map((id) => {
                        return { id: id };
                    });
                    addDef = this._applyX2ManyChange(record, fieldName, {
                        operation: 'ADD_M2M',
                        ids: values
                    }, options);
                }
                if (removedIds.length) {
                    var listData = list.data.map((localId) => self.localData[localId]);
                    removedDef = this._applyX2ManyChange(record, fieldName, {
                        operation: 'DELETE',
                        ids: removedIds.map((resID) => {
                            if (resID in list._cache) {
                                return list._cache[resID];
                            }
                            return listData.find((list) => list.res_id === resID).id;
                        }),
                    }, options);
                }
                return Promise.all([addDef, removedDef]);
            case 'MULTI':
                // allows batching multiple operations
                command.commands.forEach((innerCommand) => {
                    defs.push(self._applyX2ManyChange(
                        record,
                        fieldName,
                        innerCommand,
                        options
                    ));
                });
                break;
        }

        return Promise.all(defs).then(function () {
            // ensure to fetch up to 'limit' records (may be useful if records of
            // the current page have been removed)
            return self._readUngroupedList(list).then(function () {
                return self._fetchX2ManysBatched(list);
            });
        });
    },
    /**
     * In dataPoints of type list for x2manys, the changes are stored as a list
     * of operations (being of type 'ADD', 'DELETE', 'FORGET', UPDATE' or 'REMOVE_ALL').
     * This function applies the operation of such a dataPoint without altering
     * the original dataPoint. It returns a copy of the dataPoint in which the
     * 'count', 'data' and 'res_ids' keys have been updated.
     *
     * @private
     * @param {Object} dataPoint of type list
     * @param {Object} [options] mostly contains the range of operations to apply
     * @param {Object} [options.from=0] the index of the first operation to apply
     * @param {Object} [options.to=length] the index of the last operation to apply
     * @param {Object} [options.position] if set, each new operation will be set
     *   accordingly at the top or the bottom of the list
     * @returns {Object} element of type list in which the commands have been
     *   applied
     */
    _applyX2ManyOperations: function (list, options) {
        if (!list.static) {
            // this function only applies on x2many lists
            return list;
        }
        var self = this;
        list = Object.assign({}, list);
        list.res_ids = list.res_ids.slice(0);
        var changes = list._changes || [];
        if (options) {
            var to = options.to === 0 ? 0 : (options.to || changes.length);
            changes = changes.slice(options.from || 0, to);
        }
        changes.forEach((change) => {
            var relRecord;
            if (change.id) {
                relRecord = self.localData[change.id];
            }
            switch (change.operation) {
                case 'ADD':
                    list.count++;
                    var resID = relRecord ? relRecord.res_id : change.resID;
                    if (change.position === 'top' && (options ? options.position !== 'bottom' : true)) {
                        list.res_ids.unshift(resID);
                    } else {
                        list.res_ids.push(resID);
                    }
                    break;
                case 'FORGET':
                case 'DELETE':
                    list.count--;
                    // FIXME awa: there is no "relRecord" for o2m field
                    // seems like using change.id does the trick -> check with framework JS
                    var deletedResID = relRecord ? relRecord.res_id : change.id;
                    list.res_ids = list.res_ids.filter((resID) => resID !== deletedResID);
                    break;
                case 'REMOVE_ALL':
                    list.count = 0;
                    list.res_ids = [];
                    break;
                case 'UPDATE':
                    // nothing to do for UPDATE commands
                    break;
            }
        });
        this._setDataInRange(list);
        return list;
    },
    /**
     * Helper method to build a 'spec', that is a description of all fields in
     * the view that have a onchange defined on them.
     *
     * An onchange spec is necessary as an argument to the /onchange route. It
     * looks like this: { field: "1", anotherField: "", relation.subField: "1"}
     *
     * The first onchange call will fill up the record with default values, so
     * we need to send every field name known to us in this case.
     *
     * @see _performOnChange
     *
     * @param {Object} record resource object of type 'record'
     * @param {string} [viewType] current viewType. If not set, we will assume
     *   main viewType from the record
     * @returns {Object} with two keys
     *   - 'hasOnchange': true iff there is at least a field with onchange
     *   - 'onchangeSpec': the onchange spec
     */
    _buildOnchangeSpecs: function (record, viewType) {
        let hasOnchange = false;
        const onchangeSpec = {};
        var fieldsInfo = record.fieldsInfo[viewType || record.viewType];
        generateSpecs(fieldsInfo, record.fields);

        // recursively generates the onchange specs for fields in fieldsInfo,
        // and their subviews
        function generateSpecs(fieldsInfo, fields, prefix) {
            prefix = prefix || '';
            Object.keys(fieldsInfo).forEach((name) => {
                var field = fields[name];
                var fieldInfo = fieldsInfo[name];
                var key = prefix + name;
                onchangeSpec[key] = (field.onChange) || "";
                if (field.onChange) {
                    hasOnchange = true;
                }
                if (field.type === 'one2many' || field.type === 'many2many') {
                    Object.values(fieldInfo.views || {}).forEach((view) => {
                        generateSpecs(view.fieldsInfo[view.type], view.fields, key + '.');
                    });
                }
            });
        }
        return { hasOnchange, onchangeSpec };
    },
    /**
     * Ensures that dataPoint ids are always synchronized between the main and
     * sample models when being in sample mode. Here, we now that __id in the
     * sample model is always greater than __id in the main model (as it
     * contains strictly more datapoints).
     *
     * @override
     */
    async _callSampleModel() {
        await this._super(...arguments);
        if (this._isInSampleMode) {
            this.__id = this.sampleModel.__id;
        }
    },
    /**
     * Compute the default value that the handle field should take.
     * We need to compute this in order for new lines to be added at the correct position.
     *
     * @private
     * @param {Object} listID
     * @param {string} position
     * @return {Object} empty object if no overrie has to be done, or:
     *  field: the name of the field to override,
     *  value: the value to use for that field
     */
    _computeOverrideDefaultFields: function (listID, position) {
        var list = this.localData[listID];
        var handleField;

        // Here listID is actually just parentID, it's not yet confirmed
        // to be a list.
        // If we are not in the case that interests us,
        // listID will be undefined and this check will work.
        if (!list) {
            return {};
        }

        position = position || 'bottom';

        // Let's find if there is a field with handle.
        if (!list.fieldsInfo) {
            return {};
        }
        for (var field in list.fieldsInfo.list) {
            if (list.fieldsInfo.list[field].widget === 'handle') {
                handleField = field;
                break;
                // If there are 2 handle fields on the same list,
                // we take the first one we find.
                // And that will be alphabetically on the field name...
            }
        }

        if (!handleField) {
            return {};
        }

        // We don't want to override the default value
        // if the list is not ordered by the handle field.
        var isOrderedByHandle = list.orderedBy
            && list.orderedBy.length
            && list.orderedBy[0].asc === true
            && list.orderedBy[0].name === handleField;

        if (!isOrderedByHandle) {
            return {};
        }

        // We compute the list (get) to apply the pending changes before doing our work,
        // otherwise new lines might not be taken into account.
        // We use raw: true because we only need to load the first level of relation.
        var computedList = this.get(list.id, {raw: true});

        // We don't need to worry about the position of a new line if the list is empty.
        if (!computedList || !computedList.data || !computedList.data.length) {
            return {};
        }

        // If there are less elements in the list than the limit of
        // the page then take the index of the last existing line.

        // If the button is at the top, we want the new element on
        // the first line of the page.

        // If the button is at the bottom, we want the new element
        // after the last line of the page
        // (= theorically it will be the first element of the next page).

        // We ignore list.offset because computedList.data
        // will only have the current page elements.

        var index = Math.min(
            computedList.data.length - 1,
            position !== 'top' ? list.limit - 1 : 0
        );

        // This positioning will almost be correct. There might just be
        // an issue if several other lines have the same handleFieldValue.

        // TODO ideally: if there is an element with the same handleFieldValue,
        // that one and all the following elements must be incremented
        // by 1 (at least until there is a gap in the numbering).

        // We don't do it now because it's not an important case.
        // However, we can for sure increment by 1 if we are on the last page.
        var handleFieldValue = computedList.data[index].data[handleField];
        if (position === 'top') {
            handleFieldValue--;
        } else if (list.count <= list.offset + list.limit - (list.tempLimitIncrement || 0)) {
            handleFieldValue++;
        }
        return {
            field: handleField,
            value: handleFieldValue,
        };
    },
    /**
     * Evaluate modifiers
     *
     * @private
     * @param {Object} element a valid element object, which will serve as eval
     *   context.
     * @param {Object} modifiers
     * @returns {Object}
     * @throws {Error} if one of the modifier domains is invalid
     */
    _evalModifiers: function (element, modifiers) {
        let evalContext = null;
        const evaluated = {};
        for (const k of ['invisible', 'column_invisible', 'readonly', 'required']) {
            const mod = modifiers[k];
            if (mod === undefined || mod === false || mod === true) {
                if (k in modifiers) {
                    evaluated[k] = !!mod;
                }
                continue;
            }
            try {
                evalContext = evalContext || this._getEvalContext(element);
                evaluated[k] = new Domain(mod, evalContext).compute(evalContext);
            } catch (e) {
                throw new Error(sprintf('for modifier "%s": %s', k, e.message));
            }
        }
        return evaluated;
    },
    /**
     * Fetch the type of model (e.g. 'res.partner') contained in the model_field
     * @private
     * @param {Object} record - an element from the localData
     * @param {Object} fieldName - the name of the field
     * @param {Object} fieldInfo - the info of the field
     * @returns {Promise}
     */
    _fetchModelFieldReference: async function (record, fieldName, fieldInfo) {
        const modelField = fieldInfo.options.model_field;
        const value = record._changes && record._changes[modelField] || record.data[modelField];
        if (value) {
            if (record.fields[modelField].type !== "many2one"
                || record.fields[modelField].relation !== 'ir.model') {
                throw new Error(`The model_field of the reference field
                                 ${fieldName} must be a many2one('ir.model').`);
            }
            const modelId = this.localData[value].res_id;
            const resourceRef = record.specialData[fieldName];
            if (resourceRef && modelId === resourceRef.modelId) {
                resourceRef.hasChanged = false;
                return Promise.resolve(resourceRef);
            } else {
                const result = await this._rpc({
                    model: 'ir.model',
                    method: 'read',
                    args: [modelId, ['id', 'model']],
                });
                // Checks the case where the data on the backend side are not synchronized
                // (modelFieldName != referenceFieldName) when opening the edit view (!_changes).
                // We want to avoid resynchronization in order not to modify the data 
                // without being requested.
                if (!record._changes && record.data[fieldName]
                    && result[0].model !== this.localData[record.data[fieldName]].model) {
                    const modelFieldName = record.fields[modelField].string;
                    const referenceFieldName = record.fields[fieldName].string;

                    this.displayNotification({
                        title: sprintf(
                            _t(`'%s' is unsynchronized with '%s'.`),
                            referenceFieldName,
                            modelFieldName,
                        ),
                        message: sprintf(
                            _t(`If you change %s or %s, the synchronization will be reapplied and the data will be modified.`),
                            modelFieldName,
                            referenceFieldName,
                        ),
                        sticky: true,
                        type: 'danger',
                    });
                    return false;
                }
                return {
                    modelName: result[0].model,
                    modelId: result[0].id,
                    hasChanged: true,
                };
            }
        }
    },
    /**
     * Fetch display_name for a record datapoint.
     *
     * @param {Object} dataPoint
     * @returns {Promise}
     */
    _fetchNameGet: function (dataPoint) {
        return this._rpc({
            model: dataPoint.model,
            method: 'read',
            args: [dataPoint.res_id, ['display_name']],
            context: dataPoint.getContext(),
        }).then(function (result) {
            dataPoint.data.display_name = result[0]['display_name'];
        });
    },
    /**
     * Fetch display_name for a field of type Many2one or Reference
     *
     * @private
     * @params {Object} list: must be a datapoint of type list
     *   (for example: a datapoint representing a x2many)
     * @params {string} fieldName: the name of a field of type Many2one or Reference
     * @returns {Promise}
     */
    _fetchNameGets: function (list, fieldName) {
        var self = this;
        // We first get the model this way because if list.data is empty
        // the forEach below will not make it.
        var model = list.fields[fieldName].relation;
        var records = [];
        var ids = [];
        list = this._applyX2ManyOperations(list);

        list.data.forEach((localId) => {
            var record = self.localData[localId];
            var data = record._changes || record.data;
            var many2oneId = data[fieldName];
            if (!many2oneId) { return; }
            var many2oneRecord = self.localData[many2oneId];
            records.push(many2oneRecord);
            ids.push(many2oneRecord.res_id);
            // We need to calculate the model this way too because
            // field .relation is not set for a reference field.
            model = many2oneRecord.model;
        });

        if (!ids.length) {
            return Promise.resolve();
        }
        return this._rpc({
                model: model,
                method: 'read',
                args: [unique(ids), ['display_name']],
                context: list.context,
            })
            .then(function (readRecords) {
                records.forEach((record) => {
                    const readRecord = readRecords.find(readRecord => readRecord['id'] === record.data.id);
                    record.data.display_name = readRecord['display_name'];
                });
            });
    },
    /**
     * For a given resource of type 'record', fetch all data.
     *
     * @param {Object} record local resource
     * @param {Object} [options]
     * @param {string[]} [options.fieldNames] the list of fields to fetch. If
     *   not given, fetch all the fields in record.fieldNames (+ display_name)
     * @param {string} [options.viewType] the type of view for which the record
     *   is fetched (usefull to load the adequate fields), by defaults, uses
     *   record.viewType
     * @returns {Promise<Object>} resolves to the record or is rejected in
     *   case no id given were valid ids
     */
    _fetchRecord: function (record, options) {
        var self = this;
        options = options || {};
        var fieldNames = options.fieldNames || record.getFieldNames(options);
        fieldNames = unique(fieldNames.concat(['display_name']));
        return this._rpc({
                model: record.model,
                method: 'read',
                args: [[record.res_id], fieldNames],
                context: Object.assign({bin_size: true}, record.getContext()),
            })
            .then(function (result) {
                if (result.length === 0) {
                    return Promise.reject();
                }
                result = result[0];
                record.data = Object.assign({}, record.data, result);
            })
            .then(function () {
                self._parseServerData(fieldNames, record, record.data);
            })
            .then(function () {
                return Promise.all([
                    self._fetchX2Manys(record, options),
                    self._fetchReferences(record, options)
                ]).then(function () {
                    return self._postprocess(record, options);
                });
            });
    },
    /**
     * Fetch the `display_name` for a reference field.
     *
     * @private
     * @param {Object} record
     * @param {string} fieldName
     * @returns {Promise}
     */
    _fetchReference: function (record, fieldName) {
        var self = this;
        var def;
        var value = record._changes && record._changes[fieldName] || record.data[fieldName];
        var model = value && value.split(',')[0];
        var resID = value && parseInt(value.split(',')[1]);
        if (model && model !== 'False' && resID) {
            def = self._rpc({
                model: model,
                method: 'read',
                args: [resID, ['display_name']],
                context: record.getContext({fieldName: fieldName}),
            }).then(function (result) {
                return self._makeDataPoint({
                    data: result[0],
                    modelName: model,
                    parentID: record.id,
                });
            });
        }
        return Promise.resolve(def);
    },
    /**
     * Fetches data for reference fields and assigns these data to newly
     * created datapoint.
     * Then places datapoint reference into parent record.
     *
     * @param {Object} datapoints a collection of ids classed by model,
     *   @see _getDataToFetchByModel
     * @param {string} model
     * @param {string} fieldName
     * @returns {Promise}
     */
    _fetchReferenceData: function (datapoints, model, fieldName) {
        var self = this;
        var ids = Object.keys(datapoints).map((id) => parseInt(id));
        // we need one parent for the context (they all have the same)
        var parent = datapoints[ids[0]][0];
        var def = self._rpc({
            model: model,
            method: 'read',
            args: [ids, ['display_name']],
            context: self.localData[parent].getContext({fieldName: fieldName, withoutRecordData: true}),
        }).then(function (result) {
            result.forEach((el) => {
                var parentIDs = datapoints[el['id']];
                parentIDs.forEach((parentID) => {
                    var parent = self.localData[parentID];
                    var referenceDp = self._makeDataPoint({
                        data: el,
                        modelName: model,
                        parentID: parent.id,
                    });
                    parent.data[fieldName] = referenceDp.id;
                });
            });
        });
        return def;
    },
    /**
     * Fetch the extra data (`display_name`) for the reference fields of the record
     * model.
     *
     * @private
     * @param {Object} record
     * @returns {Promise}
     */
    _fetchReferences: function (record, options) {
        var self = this;
        var defs = [];
        var fieldNames = options && options.fieldNames || record.getFieldNames();
        fieldNames.forEach((fieldName) => {
            var field = record.fields[fieldName];
            if (field.type === 'reference') {
                var def = self._fetchReference(record, fieldName).then(function (dataPoint) {
                    if (dataPoint) {
                        record.data[fieldName] = dataPoint.id;
                    }
                });
                defs.push(def);
            }
        });
        return Promise.all(defs);
    },
    /**
     * Batch requests for one reference field in list (one request by different
     * model in the field values).
     *
     * @see _fetchReferencesBatched
     * @param {Object} list
     * @param {string} fieldName
     * @returns {Promise}
     */
    _fetchReferenceBatched: function (list, fieldName) {
        var self = this;
        list = this._applyX2ManyOperations(list);
        this._sortList(list);

        var toFetch = this._getDataToFetchByModel(list, fieldName);
        var defs = [];
        // one display_name read by model
        Object.entries(toFetch).forEach(([model, datapoints]) => {
            defs.push(self._fetchReferenceData(datapoints, model, fieldName));
        });

        return Promise.all(defs);
    },
    /**
     * Batch requests for references for datapoint of type list.
     *
     * @param {Object} list
     * @returns {Promise}
     */
    _fetchReferencesBatched: function (list) {
        var defs = [];
        var fieldNames = list.getFieldNames();
        for (var i = 0; i < fieldNames.length; i++) {
            var field = list.fields[fieldNames[i]];
            if (field.type === 'reference') {
                defs.push(this._fetchReferenceBatched(list, fieldNames[i]));
            }
        }
        return Promise.all(defs);
    },
    /**
     * Batch reference requests for all records in list.
     *
     * @see _fetchReferencesSingleBatch
     * @param {Object} list a valid resource object
     * @param {string} fieldName
     * @returns {Promise}
     */
    _fetchReferenceSingleBatch: function (list, fieldName) {
        var self = this;

        // collect ids by model
        var toFetch = {};
        list.data.forEach((groupIndex) => {
            var group = self.localData[groupIndex];
            self._getDataToFetchByModel(group, fieldName, toFetch);
        });

        var defs = [];
        // one display_name read by model
        Object.entries(toFetch).forEach(([model, datapoints]) => {
            defs.push(self._fetchReferenceData(datapoints, model, fieldName));
        });

        return Promise.all(defs);
    },
    /**
     * Batch requests for all reference field in list's children.
     * Called by _readGroup to make only one display_name 'read' rpc by fieldName.
     *
     * @param {Object} list a valid resource object
     * @returns {Promise}
     */
    _fetchReferencesSingleBatch: function (list) {
        var defs = [];
        var fieldNames = list.getFieldNames();
        for (var fIndex in fieldNames) {
            var field = list.fields[fieldNames[fIndex]];
            if (field.type === 'reference') {
                defs.push(this._fetchReferenceSingleBatch(list, fieldNames[fIndex]));
            }
        }
        return Promise.all(defs);
    },
    /**
     * Fetch model data from server, relationally to fieldName and resulted
     * field relation. For example, if fieldName is "tag_ids" and referred to
     * project.tags, it will fetch project.tags' related fields where its id is
     * contained in toFetch.ids array.
     *
     * @param {Object} list a valid resource object
     * @param {Object} toFetch a list of records and res_ids,
     *   @see _getDataToFetch
     * @param {string} fieldName
     * @returns {Promise}
     */
    _fetchRelatedData: function (list, toFetch, fieldName) {
        var self = this;
        var ids = Object.keys(toFetch || {});
        for (var i = 0; i < ids.length; i++) {
            ids[i] = Number(ids[i]);
        }
        var fieldInfo = list.fieldsInfo[list.viewType][fieldName];

        if (!ids.length || fieldInfo.__no_fetch) {
            return Promise.resolve();
        }

        var def;
        var fieldNames = Object.keys(fieldInfo.relatedFields || {});
        if (fieldNames.length) {
            var field = list.fields[fieldName];
            def = this._rpc({
                model: field.relation,
                method: 'read',
                args: [ids, fieldNames],
                context: list.getContext({withoutRecordData: true}) || {},
            });
        } else {
            def = Promise.resolve(
                ids.map((id) => {
                    return { id: id };
                })
            );
        }
        return def.then(function (result) {
            var records = unique(Object.values(toFetch || {}).flat());
            self._updateRecordsData(records, fieldName, result);
        });
    },
    /**
     * Check the AbstractField specializations that are (will be) used by the
     * given record and fetch the special data they will need. Special data are
     * data that the rendering of the record won't need if it was not using
     * particular widgets (example of these can be found at the methods which
     * start with _fetchSpecial).
     *
     * @param {Object} record - an element from the localData
     * @param {Object} options
     * @returns {Promise<Array>}
     *          The promise is resolved with an array containing the names of
     *          the field whose special data has been changed.
     */
    _fetchSpecialData: function (record, options) {
        var self = this;
        var specialFieldNames = [];
        var fieldNames = (options && options.fieldNames) || record.getFieldNames();
        return Promise.all(fieldNames.map((name) => {
            var viewType = (options && options.viewType) || record.viewType;
            var fieldInfo = record.fieldsInfo[viewType][name] || {};
            let specialData;
            if ("specialData" in fieldInfo) {
                specialData = fieldInfo.specialData;
            } else if (fieldInfo.Widget) {
                specialData = fieldInfo.Widget.prototype.specialData;
            }
            if (specialData) {
                return self[specialData](record, name, fieldInfo).then(function (data) {
                    if (data === undefined) {
                        return;
                    }
                    record.specialData[name] = data;
                    specialFieldNames.push(name);
                });
            }
        })).then(function () {
            return specialFieldNames;
        });
    },
    /**
     * Fetches all the m2o records associated to the given fieldName. If the
     * given fieldName is not a m2o field, nothing is done.
     *
     * @param {Object} record - an element from the localData
     * @param {Object} fieldName - the name of the field
     * @param {Object} fieldInfo
     * @param {string[]} [fieldsToRead] - the m2os fields to read (id and
     *                                  display_name are automatic).
     * @returns {Promise<any>}
     *          The promise is resolved with the fetched special data. If this
     *          data is the same as the previously fetched one (for the given
     *          parameters), no RPC is done and the promise is resolved with
     *          the undefined value.
     */
    _fetchSpecialMany2ones: function (record, fieldName, fieldInfo, fieldsToRead) {
        var field = record.fields[fieldName];
        if (field.type !== "many2one") {
            return Promise.resolve();
        }

        var context = record.getContext({fieldName: fieldName});
        var domain = record.getDomain({fieldName: fieldName});
        if (domain.length) {
            var localID = (record._changes && fieldName in record._changes) ?
                            record._changes[fieldName] :
                            record.data[fieldName];
            if (localID) {
                var element = this.localData[localID];
                domain = ["|", ["id", "=", element.data.id]].concat(domain);
            }
        }

        // avoid rpc if not necessary
        var hasChanged = this._saveSpecialDataCache(record, fieldName, {
            context: context,
            domain: domain,
        });
        if (!hasChanged) {
            return Promise.resolve();
        }

        return this._rpc({
                model: field.relation,
                method: 'search_read',
                fields: ["display_name"].concat(fieldsToRead || []),
                context: context,
                domain: domain,
            });
    },
    /**
     * Fetches all the relation records associated to the given fieldName. If
     * the given fieldName is not a relational field, nothing is done.
     *
     * @param {Object} record - an element from the localData
     * @param {Object} fieldName - the name of the field
     * @returns {Promise<any>}
     *          The promise is resolved with the fetched special data. If this
     *          data is the same as the previously fetched one (for the given
     *          parameters), no RPC is done and the promise is resolved with
     *          the undefined value.
     */
    _fetchSpecialRelation: function (record, fieldName) {
        var field = record.fields[fieldName];
        if (!["many2one", "many2many", "one2many"].includes(field.type)) {
            return Promise.resolve();
        }

        var context = record.getContext({fieldName: fieldName});
        var domain = record.getDomain({fieldName: fieldName});

        // avoid rpc if not necessary
        var hasChanged = this._saveSpecialDataCache(record, fieldName, {
            context: context,
            domain: domain,
        });
        if (!hasChanged) {
            return Promise.resolve();
        }

        return this._rpc({
                model: field.relation,
                method: 'name_search',
                args: ["", domain],
                context: context
            });
    },
    /**
     * Fetches the `display_name` associated to the reference widget if the field is
     * a `char` (which is a supported case).
     *
     * @private
     * @param {Object} record - an element from the localData
     * @param {Object} fieldName - the name of the field
     * @param {Object} fieldInfo - the info of the field
     * @returns {Promise}
     */
    _fetchSpecialReference: function (record, fieldName, fieldInfo) {
        var field = record.fields[fieldName];
        if (field.type === 'char') {
            // if the widget reference is set on a char field, the display_name
            // needs to be fetched a posteriori
            return Promise.resolve(this._fetchReference(record, fieldName));
        } else if (fieldInfo.options.model_field) {
            return this._fetchModelFieldReference(record, fieldName, fieldInfo);
        }
        return Promise.resolve();
    },
    /**
     * Fetches all the m2o records associated to the given fieldName. If the
     * given fieldName is not a m2o field, nothing is done. The difference with
     * _fetchSpecialMany2ones is that the field given by options.fold_field is
     * also fetched.
     *
     * @param {Object} record - an element from the localData
     * @param {Object} fieldName - the name of the field
     * @param {Object} fieldInfo
     * @returns {Promise<any>}
     *          The promise is resolved with the fetched special data. If this
     *          data is the same as the previously fetched one (for the given
     *          parameters), no RPC is done and the promise is resolved with
     *          the undefined value.
     */
    _fetchSpecialStatus: function (record, fieldName, fieldInfo) {
        var foldField = fieldInfo.options.fold_field;
        var fieldsToRead = foldField ? [foldField] : [];
        return this._fetchSpecialMany2ones(record, fieldName, fieldInfo, fieldsToRead).then(function (m2os) {
            Object.values(m2os || {}).forEach((m2o) => {
                m2o.fold = foldField ? m2o[foldField] : false;
            });
            return m2os;
        });
    },
    /**
     * Fetch all data in a ungrouped list
     *
     * @param {Object} list a valid resource object
     * @param {Object} [options]
     * @param {boolean} [options.enableRelationalFetch=true] if false, will not
     *   fetch x2m and relational data (that will be done by _readGroup in this
     *   case).
     * @returns {Promise<Object>} resolves to the fecthed list
     */
    _fetchUngroupedList: function (list, options) {
        options = Object.assign({ enableRelationalFetch: true }, options || {});
        var self = this;
        var def;
        if (list.static) {
            def = this._readUngroupedList(list).then(function () {
                if (list.parentID && self.isNew(list.parentID)) {
                    // list from a default_get, so fetch display_name for many2one fields
                    var many2ones = self._getMany2OneFieldNames(list);
                    var defs = many2ones.map((name) => self._fetchNameGets(list, name));
                    return Promise.all(defs);
                }
            });
        } else {
            def = this._searchReadUngroupedList(list);
        }
        return def.then(function () {
            if (options.enableRelationalFetch) {
                return Promise.all([
                    self._fetchX2ManysBatched(list),
                    self._fetchReferencesBatched(list)
                ]);
            }
        }).then(function () {
            return list;
        });
    },
    /**
     * batch requests for 1 x2m in list
     *
     * @see _fetchX2ManysBatched
     * @param {Object} list
     * @param {string} fieldName
     * @returns {Promise}
     */
    _fetchX2ManyBatched: function (list, fieldName) {
        list = this._applyX2ManyOperations(list);
        this._sortList(list);

        var toFetch = this._getDataToFetch(list, fieldName);
        return this._fetchRelatedData(list, toFetch, fieldName);
    },
    /**
     * X2Manys have to be fetched by separate rpcs (their data are stored on
     * different models). This method takes a record, look at its x2many fields,
     * then, if necessary, create a local resource and fetch the corresponding
     * data.
     *
     * It also tries to reuse data, if it can find an existing list, to prevent
     * useless rpcs.
     *
     * @param {Object} record local resource
     * @param {Object} [options]
     * @param {string[]} [options.fieldNames] the list of fields to fetch.
     *   If not given, fetch all the fields in record.fieldNames
     * @param {string} [options.viewType] the type of view for which the main
     *   record is fetched (useful to load the adequate fields), by defaults,
     *   uses record.viewType
     * @returns {Promise}
     */
    _fetchX2Manys: function (record, options) {
        var self = this;
        var defs = [];
        options = options || {};
        var fieldNames = options.fieldNames || record.getFieldNames(options);
        var viewType = options.viewType || record.viewType;
        fieldNames.forEach((fieldName) => {
            var field = record.fields[fieldName];
            if (field.type === 'one2many' || field.type === 'many2many') {
                var fieldInfo = record.fieldsInfo[viewType][fieldName];
                var rawContext = fieldInfo && fieldInfo.context;
                var view = fieldInfo.views && fieldInfo.views[fieldInfo.mode];
                var fieldsInfo = view ? view.fieldsInfo : (fieldInfo.fieldsInfo || {});
                var ids = record.data[fieldName] || [];

                // remove default_* & *_view_ref keys from record context
                const recordContext = { ...record.context };
                for (const key in recordContext) {
                    if (key.startsWith("default_") || key.endsWith("_view_ref")) {
                        delete recordContext[key];
                    }
                }

                var list = self._makeDataPoint({
                    count: ids.length,
                    context: Object.assign({}, recordContext, field.context),
                    fieldsInfo: fieldsInfo,
                    fields: view ? view.fields : fieldInfo.relatedFields,
                    limit: fieldInfo.limit,
                    modelName: field.relation,
                    res_ids: ids,
                    static: true,
                    type: 'list',
                    orderedBy: fieldInfo.orderedBy,
                    parentID: record.id,
                    rawContext: rawContext,
                    relationField: field.relation_field,
                    viewType: view ? view.type : fieldInfo.viewType,
                });
                record.data[fieldName] = list.id;
                if (!fieldInfo.__no_fetch) {
                    var def = self._readUngroupedList(list, { withoutRecordData: true }).then(function () {
                        return Promise.all([
                            self._fetchX2ManysBatched(list),
                            self._fetchReferencesBatched(list)
                        ]);
                    });
                    defs.push(def);
                }
            }
        });
        return Promise.all(defs);
    },
    /**
     * batch request for x2ms for datapoint of type list
     *
     * @param {Object} list
     * @returns {Promise}
     */
    _fetchX2ManysBatched: function (list) {
        var defs = [];
        var fieldNames = list.getFieldNames();
        for (var i = 0; i < fieldNames.length; i++) {
            var field = list.fields[fieldNames[i]];
            if (field.type === 'many2many' || field.type === 'one2many') {
                defs.push(this._fetchX2ManyBatched(list, fieldNames[i]));
            }
        }
        return Promise.all(defs);
    },
    /**
     * For a non-static list, batches requests for all its sublists' records.
     * Make only one rpc for all records on the concerned field.
     *
     * @see _fetchX2ManysSingleBatch
     * @param {Object} list a valid resource object, its data must be another
     *   list containing records
     * @param {string} fieldName
     * @returns {Promise}
     */
    _fetchX2ManySingleBatch: function (list, fieldName) {
        var self = this;
        var toFetch = {};
        list.data.forEach((groupIndex) => {
            var group = self.localData[groupIndex];
            var nextDataToFetch = self._getDataToFetch(group, fieldName);
            Object.keys(nextDataToFetch).forEach((id) => {
                if (toFetch[id]) {
                    toFetch[id] = toFetch[id].concat(nextDataToFetch[id]);
                } else {
                    toFetch[id] = nextDataToFetch[id];
                }
            });
        });
        return self._fetchRelatedData(list, toFetch, fieldName);
    },
    /**
     * Batch requests for all x2m in list's children.
     * Called by _readGroup to make only one 'read' rpc by fieldName.
     *
     * @param {Object} list a valid resource object
     * @returns {Promise}
     */
    _fetchX2ManysSingleBatch: function (list) {
        var defs = [];
        var fieldNames = list.getFieldNames();
        for (var i = 0; i < fieldNames.length; i++) {
            var field = list.fields[fieldNames[i]];
            if (field.type === 'many2many' || field.type === 'one2many'){
                defs.push(this._fetchX2ManySingleBatch(list, fieldNames[i]));
            }
        }
        return Promise.all(defs);
    },
    /**
     * Generates an object mapping field names to their changed value in a given
     * record (i.e. maps to the new value for basic fields, to the res_id for
     * many2ones and to commands for x2manys).
     *
     * @private
     * @param {Object} record
     * @param {Object} [options]
     * @param {boolean} [options.changesOnly=true] if true, only generates
     *   commands for fields that have changed (concerns x2many fields only)
     * @param {boolean} [options.withReadonly=false] if false, doesn't generate
     *   changes for readonly fields
     * @param {string} [options.viewType] current viewType. If not set, we will
     *   assume main viewType from the record. Note that if an editionViewType is
     *   specified for a field, it will take the priority over the viewType arg.
     * @returns {Object} a map from changed fields to their new value
     */
    _generateChanges: function (record, options) {
        options = options || {};
        var viewType = options.viewType || record.viewType;
        var changes;
        const changesOnly = 'changesOnly' in options ? !!options.changesOnly : true;
        if (!changesOnly) {
            changes = Object.assign({}, record.data, record._changes);
        } else {
            changes = Object.assign({}, record._changes);
        }
        var withReadonly = options.withReadonly || false;
        var commands = this._generateX2ManyCommands(record, {
            changesOnly: changesOnly,
            withReadonly: withReadonly,
        });
        for (var fieldName in record.fields) {
            // remove readonly fields from the list of changes
            if (!withReadonly && fieldName in changes || fieldName in commands) {
                var editionViewType = record._editionViewType[fieldName] || viewType;
                if (this._isFieldProtected(record, fieldName, editionViewType)) {
                    delete changes[fieldName];
                    continue;
                }
            }

            // process relational fields and handle the null case
            var type = record.fields[fieldName].type;
            var value;
            if (type === 'one2many' || type === 'many2many') {
                if (!changesOnly || (commands[fieldName] && commands[fieldName].length)) { // replace localId by commands
                    changes[fieldName] = commands[fieldName];
                } else { // no command -> no change for that field
                    delete changes[fieldName];
                }
            } else if (type === 'many2one' && fieldName in changes) {
                value = changes[fieldName];
                changes[fieldName] = value ? this.localData[value].res_id : false;
            } else if (type === 'reference' && fieldName in changes) {
                value = changes[fieldName];
                changes[fieldName] = value ?
                    this.localData[value].model + ',' + this.localData[value].res_id :
                    false;
            } else if (type === 'char' && changes[fieldName] === '') {
                changes[fieldName] = false;
            } else if (changes[fieldName] === null) {
                changes[fieldName] = false;
            }
        }
        return changes;
    },
    /**
     * Generates an object mapping field names to their current value in a given
     * record. If the record is inside a one2many, the returned object contains
     * an additional key (the corresponding many2one field name) mapping to the
     * current value of the parent record.
     *
     * @param {Object} record
     * @param {Object} [options] This option object will be given to the private
     *   method _generateX2ManyCommands.  In particular, it is useful to be able
     *   to send changesOnly:true to get all data, not only the current changes.
     * @returns {Object} the data
     */
    _generateOnChangeData: function (record, options) {
        options = Object.assign({}, options || {}, {withReadonly: true});
        var data = {};
        if (!options.firstOnChange) {
            var commands = this._generateX2ManyCommands(record, options);
            data = Object.assign(this.get(record.id, {raw: true}).data, commands);
            // 'display_name' is automatically added to the list of fields to fetch,
            // when fetching a record, even if it doesn't appear in the view. However,
            // only the fields in the view must be passed to the onchange RPC, so we
            // remove it from the data sent by RPC if it isn't in the view.
            var hasDisplayName = Object.values(record.fieldsInfo || {}).some((fieldsInfo) => {
                return 'display_name' in fieldsInfo;
            });
            if (!hasDisplayName) {
                delete data.display_name;
            }
        }

        // one2many records have a parentID
        if (record.parentID) {
            var parent = this.localData[record.parentID];
            // parent is the list element containing all the records in the
            // one2many and parent.parentID is the ID of the main record
            // if there is a relation field, this means that record is an elem
            // in a one2many. The relation field is the corresponding many2one
            if (parent.parentID && parent.relationField) {
                var parentRecord = this.localData[parent.parentID];
                data[parent.relationField] = this._generateOnChangeData(parentRecord);
            }
        }

        return data;
    },
    /**
     * Read all x2many fields and generate the commands for the server to create
     * or write them...
     *
     * @param {Object} record
     * @param {Object} [options]
     * @param {string} [options.fieldNames] if given, generates the commands for
     *   these fields only
     * @param {boolean} [changesOnly=false] if true, only generates commands for
     *   fields that have changed
     * @param {boolean} [options.withReadonly=false] if false, doesn't generate
     *   changes for readonly fields in commands
     * @returns {Object} a map from some field names to commands
     */
    _generateX2ManyCommands: function (record, options) {
        var self = this;
        options = options || {};
        const changesOnly = options.changesOnly;
        var fields = record.fields;
        if (options.fieldNames) {
            fields = pick(fields, ...options.fieldNames);
        }
        var commands = {};
        var data = Object.assign({}, record.data, record._changes);
        var type;
        for (var fieldName in fields) {
            type = fields[fieldName].type;

            if (type === 'many2many' || type === 'one2many') {
                if (!data[fieldName]) {
                    // skip if this field is empty
                    continue;
                }
                commands[fieldName] = [];
                var list = this.localData[data[fieldName]];
                if (options.changesOnly && (!list._changes || !list._changes.length)) {
                    // if only changes are requested, skip if there is no change
                    continue;
                }
                var oldResIDs = list.res_ids.slice(0);
                var relRecordAdded = [];
                var relRecordUpdated = [];
                Object.values(list._changes || {}).forEach((change) => {
                    if (change.operation === 'ADD' && change.id) {
                        relRecordAdded.push(self.localData[change.id]);
                    } else if (change.operation === 'UPDATE' && !self.isNew(change.id)) {
                        // ignore new records that would have been updated
                        // afterwards, as all their changes would already
                        // be aggregated in the CREATE command
                        relRecordUpdated.push(self.localData[change.id]);
                    }
                });
                list = this._applyX2ManyOperations(list);
                this._sortList(list);
                if (type === 'many2many' || list._forceM2MLink) {
                    var relRecordCreated = relRecordAdded.filter(rec => typeof rec.res_id === 'string');
                    const relRecordCreatedResId = relRecordCreated.map(r => r.res_id)
                    var realIDs = list.res_ids.filter((x) => relRecordCreatedResId.indexOf(x) < 0)
                    // deliberately generate a single 'replace' command instead
                    // of a 'delete' and a 'link' commands with the exact diff
                    // because 1) performance-wise it doesn't change anything
                    // and 2) to guard against concurrent updates (policy: force
                    // a complete override of the actual value of the m2m)
                    commands[fieldName].push(x2ManyCommands.replace_with(realIDs));
                    relRecordCreated.forEach((relRecord) => {
                        var changes = self._generateChanges(relRecord, options);
                        commands[fieldName].push(x2ManyCommands.create(relRecord.ref, changes));
                    });
                    // generate update commands for records that have been
                    // updated (it may happen with editable lists)
                    relRecordUpdated.forEach((relRecord) => {
                        var changes = self._generateChanges(relRecord, options);
                        if (Object.keys(changes || {}).length > 0) {
                            var command = x2ManyCommands.update(relRecord.res_id, changes);
                            commands[fieldName].push(command);
                        }
                    });
                } else if (type === 'one2many') {
                    var removedIds = oldResIDs.filter((x) => list.res_ids.indexOf(x) < 0);
                    var addedIds = list.res_ids.filter((x) => oldResIDs.indexOf(x) < 0);
                    var keptIds = intersection(oldResIDs, list.res_ids);

                    // the didChange variable keeps track of the fact that at
                    // least one id was updated
                    var didChange = false;
                    var changes, command, relRecord;
                    for (var i = 0; i < list.res_ids.length; i++) {
                        if (keptIds.includes(list.res_ids[i])) {
                            // this is an id that already existed
                            relRecord = relRecordUpdated.find((record) => record.res_id === list.res_ids[i]);
                            changes = relRecord ? this._generateChanges(relRecord, options) : {};
                            if (Object.keys(changes || {}).length > 0) {
                                command = x2ManyCommands.update(relRecord.res_id, changes);
                                didChange = true;
                            } else {
                                command = x2ManyCommands.link_to(list.res_ids[i]);
                            }
                            commands[fieldName].push(command);
                        } else if (addedIds.includes(list.res_ids[i])) {
                            // this is a new id (maybe existing in DB, but new in JS)
                            relRecord = relRecordAdded.find((record) => record.res_id === list.res_ids[i]);
                            if (!relRecord) {
                                commands[fieldName].push(x2ManyCommands.link_to(list.res_ids[i]));
                                continue;
                            }
                            changes = this._generateChanges(relRecord, options);
                            if (!this.isNew(relRecord.id)) {
                                // the subrecord already exists in db
                                commands[fieldName].push(x2ManyCommands.link_to(relRecord.res_id));
                                if (changesOnly ? Object.keys(changes).length : this.isDirty(relRecord.id)) {
                                    delete changes.id;
                                    commands[fieldName].push(x2ManyCommands.update(relRecord.res_id, changes));
                                }
                            } else {
                                // the subrecord is new, so create it

                                // we may have received values from an onchange for fields that are
                                // not in the view, and that we don't even know, as we don't have the
                                // fields_get of models of related fields. We save those values
                                // anyway, but for many2ones, we have to extract the id from the pair
                                // [id, display_name]
                                const rawChangesEntries = Object.entries(relRecord._rawChanges);
                                for (const [fieldName, value] of rawChangesEntries) {
                                    const isMany2OneValue = Array.isArray(value) &&
                                                            value.length === 2 &&
                                                            Number.isInteger(value[0]) &&
                                                            typeof value[1] === 'string';
                                    changes[fieldName] = isMany2OneValue ? value[0] : value;
                                }

                                commands[fieldName].push(x2ManyCommands.create(relRecord.ref, changes));
                            }
                        }
                    }
                    if (options.changesOnly && !didChange && addedIds.length === 0 && removedIds.length === 0) {
                        // in this situation, we have no changed ids, no added
                        // ids and no removed ids, so we can safely ignore the
                        // last changes
                        commands[fieldName] = [];
                    }
                    // add delete commands
                    for (i = 0; i < removedIds.length; i++) {
                        if (list._forceM2MUnlink) {
                            commands[fieldName].push(x2ManyCommands.forget(removedIds[i]));
                        } else {
                            commands[fieldName].push(x2ManyCommands.delete(removedIds[i]));
                        }
                    }
                }
            }
        }
        return commands;
    },
    /**
     * Every RPC done by the model need to add some context, which is a
     * combination of the context of the session, of the record/list, and/or of
     * the concerned field. This method combines all these contexts and evaluate
     * them with the proper evalcontext.
     *
     * @param {Object} element an element from the localData
     * @param {Object} [options]
     * @param {string|Object} [options.additionalContext]
     *        another context to evaluate and merge to the returned context
     * @param {string} [options.fieldName]
     *        if given, this field's context is added to the context, instead of
     *        the element's context (except if options.full is true)
     * @param {boolean} [options.full=false]
     *        if true or nor fieldName or additionalContext given in options,
     *        the element's context is added to the context
     * @param {boolean} [options.withoutRecordData=false]
     *        if true the record data will be replaced by a sentinel in the eval
     *        context (useful for read rpcs, where we don't want the context to
     *        depend on data)
     * @returns {Object} the evaluated context
     */
    _getContext: function (element, options) {
        options = options || {};
        var context = new Context(session.user_context);

        if (options.full || !(options.fieldName || options.additionalContext)) {
            const keys_to_omit = Object.keys(element.context || {}).filter((key) => String(key).startsWith('default_'));
            var context_to_add = options.sanitize_default_values ?
                omit(element.context, ...keys_to_omit)
                : element.context;
            context.add(context_to_add);
        }
        if (options.fieldName) {
            var viewType = options.viewType || element.viewType;
            var fieldInfo = element.fieldsInfo[viewType][options.fieldName];
            if (fieldInfo && fieldInfo.context) {
                if (fieldInfo.context !== "{}") {
                    context.add(fieldInfo.context);
                }
            } else {
                var fieldParams = element.fields[options.fieldName];
                if (fieldParams.context) {
                    context.add(fieldParams.context);
                }
            }
        }
        if (element.rawContext) {
            var rawContext = new Context(element.rawContext);
            var evalContext = this._getEvalContext(this.localData[element.parentID], false, options.withoutRecordData);
            evalContext.id = evalContext.id || false;
            rawContext.set_eval_context(evalContext);
            context.add(rawContext);
        }
        if (options.additionalContext) {
            context.add(options.additionalContext);
        }

        if (context.__contexts.length > 1) {
            context.set_eval_context(this._getEvalContext(element, false, options.withoutRecordData));
            const evaluatedContext = context.eval();
            if (options.withoutRecordData) {
                for (const key in evaluatedContext) {
                    if (evaluatedContext[key] === SENTINEL) {
                        delete evaluatedContext[key];
                    }
                }
                if (evaluatedContext.parent) {
                    for (const key in evaluatedContext.parent) {
                        if (evaluatedContext.parent[key] === SENTINEL) {
                            delete evaluatedContext.parent[key];
                        }
                    }
                }
            }
            return evaluatedContext;
        } else {
            return Object.assign({}, session.user_context);
        }
    },
    /**
     * Collects from a record a list of ids to fetch, according to fieldName,
     * and a list of records where to set the result of the fetch.
     *
     * @param {Object} list a list containing records we want to get the ids,
     *   it assumes _applyX2ManyOperations and _sort have been already called on
     *   this list
     * @param {string} fieldName
     * @return {Object} a list of records and res_ids
     */
    _getDataToFetch: function (list, fieldName) {
        var self = this;
        var field = list.fields[fieldName];
        var fieldInfo = list.fieldsInfo[list.viewType][fieldName];
        var view = fieldInfo.views && fieldInfo.views[fieldInfo.mode];
        var fieldsInfo = view ? view.fieldsInfo : fieldInfo.fieldsInfo;
        var fields = view ? view.fields : fieldInfo.relatedFields;
        var viewType = view ? view.type : fieldInfo.viewType;

        var toFetch = {};

        // flattens the list.data ids in a grouped case
        let dataPointIds = list.data;
        for (let i = 0; i < list.groupedBy.length; i++) {
            dataPointIds = dataPointIds.reduce((acc, groupId) =>
                acc.concat(this.localData[groupId].data), []);
        }

        dataPointIds.forEach(function (dataPoint) {
            var record = self.localData[dataPoint];
            if (typeof record.data[fieldName] === 'string'){
                // in this case, the value is a local ID, which means that the
                // record has already been processed. It can happen for example
                // when a user adds a record in a m2m relation, or loads more
                // records in a kanban column
                return;
            }

            Object.values(record.data[fieldName] || {}).forEach((id) => {
                toFetch[id] = toFetch[id] || [];
                toFetch[id].push(record);
            });

            var m2mList = self._makeDataPoint({
                fieldsInfo: fieldsInfo,
                fields: fields,
                modelName: field.relation,
                parentID: record.id,
                res_ids: record.data[fieldName],
                static: true,
                type: 'list',
                viewType: viewType,
            });
            record.data[fieldName] = m2mList.id;
        });

        return toFetch;
    },
    /**
     * Determines and returns from a list a collection of ids classed by
     * their model.
     *
     * @param {Object} list a valid resource object
     * @param {string} fieldName
     * @param {Object} [toFetchAcc] an object to store fetching data. Used when
     *  batching reference across multiple groups.
     *    [modelName: string]: {
     *        [recordId: number]: datapointId[]
     *    }
     * @returns {Object} each key represent a model and contain a sub-object
     * where each key represent an id (res_id) containing an array of
     * webclient id (referred to a datapoint, so not a res_id).
     */
    _getDataToFetchByModel: function (list, fieldName, toFetchAcc) {
        var self = this;
        var toFetch = toFetchAcc || {};
        list.data.forEach((dataPoint) => {
            var record = self.localData[dataPoint];
            var value = record.data[fieldName];
            // if the reference field has already been fetched, the value is a
            // datapoint ID, and in this case there's nothing to do
            if (value && !self.localData[value]) {
                var model = value.split(',')[0];
                var resID = value.split(',')[1];
                if (!(model in toFetch)) {
                    toFetch[model] = {};
                }
                // there could be multiple datapoints with the same model/resID
                if (toFetch[model][resID]) {
                    toFetch[model][resID].push(dataPoint);
                } else {
                    toFetch[model][resID] = [dataPoint];
                }
            }
        });
        return toFetch;
    },
    /**
     * Given a dataPoint of type list (that may be a group), returns an object
     * with 'default_' keys to be used to create new records in that group.
     *
     * @private
     * @param {Object} dataPoint
     * @returns {Object}
     */
    _getDefaultContext: function (dataPoint) {
        var defaultContext = {};
        while (dataPoint.parentID) {
            var parent = this.localData[dataPoint.parentID];
            var groupByField = parent.groupedBy[0].split(':')[0];
            var value = viewUtils.getGroupValue(dataPoint, parent.groupedBy[0]);
            if (value) {
                defaultContext['default_' + groupByField] = value;
            }
            dataPoint = parent;
        }
        return defaultContext;
    },
    /**
     * Some records are associated to a/some domain(s). This method allows to
     * retrieve them, evaluated.
     *
     * @param {Object} element an element from the localData
     * @param {Object} [options]
     * @param {string} [options.fieldName]
     *        the name of the field whose domain needs to be returned
     * @returns {Array} the evaluated domain
     */
    _getDomain: function (element, options) {
        if (options && options.fieldName) {
            if (element._domains[options.fieldName]) {
                return Domain.prototype.stringToArray(
                    element._domains[options.fieldName],
                    this._getEvalContext(element, true)
                );
            }
            var viewType = options.viewType || element.viewType;
            var fieldInfo = element.fieldsInfo[viewType][options.fieldName];
            if (fieldInfo && fieldInfo.domain) {
                return Domain.prototype.stringToArray(
                    fieldInfo.domain,
                    this._getEvalContext(element, true)
                );
            }
            var fieldParams = element.fields[options.fieldName];
            if (fieldParams.domain) {
                return Domain.prototype.stringToArray(
                    fieldParams.domain,
                    this._getEvalContext(element, true)
                );
            }
            return [];
        }

        return Domain.prototype.stringToArray(
            element.domain,
            this._getEvalContext(element, true)
        );
    },
    /**
     * Returns the evaluation context that should be used when evaluating the
     * context/domain associated to a given element from the localData.
     *
     * It is actually quite subtle.  We need to add some magic keys: active_id
     * and active_ids.  Also, the session user context is added in the mix to be
     * sure.  This allows some domains to use the uid key for example
     *
     * @param {Object} element - an element from the localData
     * @param {boolean} [forDomain=false] if true, evaluates x2manys as a list of
     *   ids instead of a list of commands
     * @param {boolean} [withoutRecordData=false] if true, replaces the record
     *   values by null (same inside the parent key)
     * @returns {Object}
     */
    _getEvalContext: function (element, forDomain, withoutRecordData) {
        var evalContext = element.type === 'record' ? this._getRecordEvalContext(element, forDomain) : {};
        if (withoutRecordData) {
            const entries = Object.keys(evalContext).map((key) => [key, SENTINEL]);
            evalContext = Object.fromEntries(entries);
        }
        if (element.parentID) {
            var parent = this.localData[element.parentID];
            if (parent.type === 'list' && parent.parentID) {
                parent = this.localData[parent.parentID];
            }
            if (parent.type === 'record') {
                evalContext.parent = this._getRecordEvalContext(parent, forDomain);
                if (withoutRecordData) {
                    const entries = Object.keys(evalContext.parent).map((key) => [key, SENTINEL]);
                    evalContext.parent = Object.fromEntries(entries);
                }
            }
        }
        // Uses "current_company_id" because "company_id" would conflict with all the company_id fields
        // in general, the actual "company_id" field of the form should be used for m2o domains, not this fallback
        let current_company_id;
        if (session.user_context.allowed_company_ids) {
            current_company_id = session.user_context.allowed_company_ids[0];
        } else {
            current_company_id = session.user_companies ?
                session.user_companies.current_company :
                false;
        }
        return Object.assign(
            {
                active_id: evalContext.id || false,
                active_ids: evalContext.id ? [evalContext.id] : [],
                active_model: element.model,
                current_company_id,
                id: evalContext.id || false,
            },
            session.user_context,
            element.context,
            evalContext,
        );
    },

    _getLazyEvalContext: function (element, forDomain) {
        var evalContext = element.type === 'record' ? this._getLazyRecordEvalContext(element, forDomain) : {};

        if (element.parentID) {
            var parent = this.localData[element.parentID];
            if (parent.type === 'list' && parent.parentID) {
                parent = this.localData[parent.parentID];
            }
            if (parent.type === 'record') {
                evalContext.parent = this._getLazyRecordEvalContext(parent, forDomain);
            }
        }
        // Uses "current_company_id" because "company_id" would conflict with all the company_id fields
        // in general, the actual "company_id" field of the form should be used for m2o domains, not this fallback
        let current_company_id;
        if (session.user_context.allowed_company_ids) {
            current_company_id = session.user_context.allowed_company_ids[0];
        } else {
            current_company_id = session.user_companies ?
                session.user_companies.current_company :
                false;
        }
        let fallbackContext = Object.assign(
            {
                active_id: evalContext.id || false,
                active_ids: evalContext.id ? [evalContext.id] : [],
                active_model: element.model,
                current_company_id,
                id: evalContext.id || false,
            },
            session.user_context,
            element.context,
        );

        return new Proxy(
            {}, {
                has(target, key) {
                    return key in target || key in evalContext || key in fallbackContext;
                },
                get (target, key) {
                    switch (true) {
                        case key in target:
                            return target[key];
                        case key in evalContext:
                            return evalContext[key];
                        default:
                            return fallbackContext[key];;
                    }
                },
                ownKeys(target) {
                    return [...new Set([...Reflect.ownKeys(target), ...Object.keys(fallbackContext), ...Object.keys(evalContext)])];
                },
                getOwnPropertyDescriptor(target, prop) {
                    return Reflect.getOwnPropertyDescriptor(target, prop) || { writable: true, configurable: true, enumerable: true };
                },
            }
        );
    },
    /**
     * Returns the list of field names of the given element according to its
     * default view type.
     *
     * @param {Object} element an element from the localData
     * @param {Object} [options]
     * @param {Object} [options.viewType] current viewType. If not set, we will
     *   assume main viewType from the record
     * @returns {string[]} the list of field names
     */
    _getFieldNames: function (element, options) {
        var fieldsInfo = element.fieldsInfo;
        var viewType = options && options.viewType || element.viewType;
        return Object.keys(fieldsInfo && fieldsInfo[viewType] || {});
    },
    /**
     * Get a subset of a list resource keeping only the props to keep.
     * This permits to a web_read_group to keep some of the properties
     * of a previous list if it is still in its results.
     *
     * @private
     * @param {Object} list
     * @param {boolean} options.onlyGroup true when we only fetched the group's own data
     * @param {boolean} options.hasSubgroups true when the fetched group has subgroups
     * @returns {Object} subset of list
     */
    _getGroupedListPropsToKeep(list, options) {
        const { isOpen, offset, id } = list;
        let propsToKeep = { isOpen, offset, id };

        if (options.onlyGroup || isOpen && options.hasSubgroups) {
            // If the group is opened and contains subgroups,
            // also keep its data to keep internal state of
            // sub-groups
            // Also keep data if we only reload groups' own data
            propsToKeep.data = list.data;
            if (options.onlyGroup) {
                // keep count and res_ids as in this case the group
                // won't be search_read again. This situation happens
                // when using kanban quick_create where the record is manually
                // added to the datapoint before getting here.
                propsToKeep.res_ids = list.res_ids;
                propsToKeep.count = list.count;
            }
        }

        return propsToKeep;
    },
    /**
     * Get many2one fields names in a datapoint. This is useful in order to
     * fetch their names in the case of a default_get.
     *
     * @private
     * @param {Object} datapoint a valid resource object
     * @returns {string[]} list of field names that are many2one
     */
    _getMany2OneFieldNames: function (datapoint) {
        var many2ones = [];
        for (const [name, field] of Object.entries(datapoint.fields)) {
            if (field.type === 'many2one') {
                many2ones.push(name);
            }
        }
        return many2ones;
    },
    /**
     * Evaluate the record evaluation context.  This method is supposed to be
     * called by _getEvalContext.  It basically only generates a dictionary of
     * current values for the record, with commands for x2manys fields.
     *
     * @param {Object} record an element of type 'record'
     * @returns Object
     */
    _getRecordEvalContext: function (record) {
        var relDataPoint;
        var context = Object.assign({}, record.data, record._changes);

        for (var fieldName in context) {
            var field = record.fields[fieldName];
            if (context[fieldName] === null) {
                context[fieldName] = false;
            }
            if (!field || field.name === 'id') {
                continue;
            }
            if (field.type === 'date' || field.type === 'datetime') {
                if (context[fieldName]) {
                    context[fieldName] = JSON.parse(JSON.stringify(context[fieldName]));
                }
                continue;
            }
            if (field.type === 'many2one') {
                relDataPoint = this.localData[context[fieldName]];
                context[fieldName] = relDataPoint ? relDataPoint.res_id : false;
                continue;
            }
            if (field.type === 'one2many' || field.type === 'many2many') {
                var ids;
                if (!context[fieldName] || Array.isArray(context[fieldName])) { // no dataPoint created yet
                    ids = context[fieldName] ? context[fieldName].slice(0) : [];
                } else {
                    relDataPoint = this._applyX2ManyOperations(this.localData[context[fieldName]]);
                    ids = relDataPoint.res_ids.slice(0);
                }
                if (field.type === 'one2many') { // Ids are evaluated as a list of ids
                    /* Filtering out virtual ids from the ids list
                     * The server will crash if there are virtual ids in there
                     * The webClient doesn't do literal id list comparison like ids == list
                     * Only relevant in o2m: m2m does create actual records in db
                     */
                    ids = ids.filter(id => typeof id !== 'string');
                }
                context[fieldName] = ids;
            }

        }
        return context;
    },

    _getLazyRecordEvalContext: function (record) {
        let self = this;
        let relDataPoint;

        return new Proxy({}, {
            has(target, key) {
                return key in target || key in record.fields;
            },
            ownKeys(target) {
                return [...new Set([...Reflect.ownKeys(target), ...Object.keys(record.fields)])];
            },
            getOwnPropertyDescriptor(target, prop) {
                return Reflect.getOwnPropertyDescriptor(target, prop) || { writable: true, configurable: true, enumerable: true };
            },
            get( target, fieldName ) {
                if (fieldName in target){
                    return target[fieldName];
                }
                const fieldValue = record._changes && fieldName in record._changes ? record._changes[fieldName] : record.data[fieldName];
                const field = record.fields[fieldName];
                if (fieldValue === null) {
                    return false;
                }
                if (fieldName === "id" && !fieldValue) {
                    return false;
                }

                if (field.type === 'date' || field.type === 'datetime') {
                    if (fieldValue) {
                        return JSON.parse(JSON.stringify(fieldValue));
                    }
                }
                if (field.type === 'many2one') {
                    relDataPoint = self.localData[fieldValue];
                    return relDataPoint ? relDataPoint.res_id : false;
                }
                if (field.type === 'one2many' || field.type === 'many2many') {
                    let ids;
                    if (!fieldValue || Array.isArray(fieldValue)) { // no dataPoint created yet
                        ids = fieldValue ? fieldValue.slice(0) : [];
                    } else {
                        relDataPoint = self._applyX2ManyOperations(self.localData[fieldValue]);
                        ids = relDataPoint.res_ids.slice(0);
                    }
                    if (field.type === 'one2many') { // Ids are evaluated as a list of ids
                        /* Filtering out virtual ids from the ids list
                        * The server will crash if there are virtual ids in there
                        * The webClient doesn't do literal id list comparison like ids == list
                        * Only relevant in o2m: m2m does create actual records in db
                        */
                        ids = ids.filter(id => typeof id !== 'string');
                    }
                    return ids;
                }
                if (field.type === "properties" && Array.isArray(fieldValue)) {
                    // remove deleted properties to be able
                    // to filter based on empty properties field
                    return fieldValue.filter(definition => !definition.definition_deleted);
                }
                return fieldValue;
            }
        });
    },
    /**
     * Get the domain for a list resource.
     *
     * @private
     * @param {Object} list
     * @returns {Array[]} list domain
     */
    _getUngroupedListDomain(list) {
        return list.domain || [];
    },
    /**
     * Returns true if the field is protected against changes, looking for a
     * readonly modifier unless there is a force_save modifier (checking first
     * in the modifiers, and if there is no readonly modifier, checking the
     * readonly attribute of the field).
     *
     * @private
     * @param {Object} record an element from the localData
     * @param {string} fieldName
     * @param {string} [viewType] current viewType. If not set, we will assume
     *   main viewType from the record
     * @returns {boolean}
     */
    _isFieldProtected: function (record, fieldName, viewType) {
        viewType = viewType || record.viewType;
        var fieldInfo = viewType && record.fieldsInfo && record.fieldsInfo[viewType][fieldName];
        if (fieldInfo) {
            var rawModifiers = fieldInfo.modifiers || {};
            var modifiers = this._evalModifiers(record, pick(rawModifiers, 'readonly'));
            return modifiers.readonly && !fieldInfo.force_save;
        } else {
            return false;
        }
    },
    /**
     * Returns true iff value is considered to be set for the given field's type.
     *
     * @private
     * @param {any} value a value for the field
     * @param {string} fieldType a type of field
     * @returns {boolean}
     */
    _isFieldSet: function (value, fieldType) {
        switch (fieldType) {
            case 'boolean':
                return true;
            case 'one2many':
            case 'many2many':
                return value.length > 0;
            default:
                return value !== false;
        }
    },
    /**
     * return true if a list element is 'valid'. Such an element is valid if it
     * has no sub record with an unset required field.
     *
     * This method is meant to be used to check if a x2many change will trigger
     * an onchange.
     *
     * @param {string} id id for a local resource of type 'list'. This is
     *   assumed to be a list element for an x2many
     * @returns {boolean}
     */
    _isX2ManyValid: function (id) {
        var self = this;
        var isValid = true;
        var element = this.localData[id];
        Object.values(element._changes || {}).forEach((command) => {
            if (command.operation === 'DELETE' ||
                    command.operation === 'FORGET' ||
                    (command.operation === 'ADD' &&  !command.isNew)||
                    command.operation === 'REMOVE_ALL') {
                return;
            }
            var recordData = self.get(command.id, {raw: true}).data;
            var record = self.localData[command.id];
            element.getFieldNames().forEach((fieldName) => {
                var field = element.fields[fieldName];
                var fieldInfo = element.fieldsInfo[element.viewType][fieldName];
                var rawModifiers = fieldInfo.modifiers || {};
                var modifiers = self._evalModifiers(record, pick(rawModifiers, 'required'));
                if (modifiers.required && !self._isFieldSet(recordData[fieldName], field.type)) {
                    isValid = false;
                }
            });
        });
        return isValid;
    },
    /**
     * Helper method for the load entry point.
     *
     * @see load
     *
     * @param {Object} dataPoint some local resource
     * @param {Object} [options]
     * @param {string[]} [options.fieldNames] the fields to fetch for a record
     * @param {boolean} [options.onlyGroups=false]
     * @param {boolean} [options.keepEmptyGroups=false] if set, the groups not
     *   present in the read_group anymore (empty groups) will stay in the
     *   datapoint (used to mimic the kanban renderer behaviour for example)
     * @returns {Promise}
     */
    _load: function (dataPoint, options) {
        if (options && options.onlyGroups &&
          !(dataPoint.type === 'list' && dataPoint.groupedBy.length)) {
            return Promise.resolve(dataPoint);
        }

        if (dataPoint.type === 'record') {
            return this._fetchRecord(dataPoint, options);
        }
        if (dataPoint.type === 'list' && dataPoint.groupedBy.length) {
            return this._readGroup(dataPoint, options);
        }
        if (dataPoint.type === 'list' && !dataPoint.groupedBy.length) {
            return this._fetchUngroupedList(dataPoint, options);
        }
    },
    /**
     * Turns a bag of properties into a valid local resource.  Also, register
     * the resource in the localData object.
     *
     * @param {Object} params
     * @param {Object} [params.aggregateValues={}]
     * @param {Object} [params.context={}] context of the action
     * @param {integer} [params.count=0] number of record being manipulated
     * @param {Object|Object[]} [params.data={}|[]] data of the record
     * @param {*[]} [params.domain=[]]
     * @param {Object} params.fields contains the description of each field
     * @param {Object} [params.fieldsInfo={}] contains the fieldInfo of each field
     * @param {Object[]} [params.fieldNames] the name of fields to load, the list
     *   of all fields by default
     * @param {string[]} [params.groupedBy=[]]
     * @param {boolean} [params.isOpen]
     * @param {integer} params.limit max number of records shown on screen (pager size)
     * @param {string} params.modelName
     * @param {integer} [params.offset]
     * @param {boolean} [params.openGroupByDefault]
     * @param {Object[]} [params.orderedBy=[]]
     * @param {integer[]} [params.orderedResIDs]
     * @param {string} [params.parentID] model name ID of the parent model
     * @param {Object} [params.rawContext]
     * @param {[type]} [params.ref]
     * @param {string} [params.relationField]
     * @param {integer|null} [params.res_id] actual id of record in the server
     * @param {integer[]} [params.res_ids] context in which the data point is used, from a list of res_id
     * @param {boolean} [params.static=false]
     * @param {string} [params.type='record'|'list']
     * @param {[type]} [params.value]
     * @param {Object} [params.range] only for datapoints representing groups
     *   coming from a groupBy on a date(time) field @see _readGroup format:
     *   {[fieldName:granularity]: {from: string, to: string}}, where
     *   'from' (inclusive) and 'to' (exclusive) are the group bounds under the
     *   respective date format
     * @param {string} [params.viewType] the type of the view, e.g. 'list' or 'form'
     * @returns {Object} the resource created
     */
    _makeDataPoint: function (params) {
        var type = params.type || ('domain' in params && 'list') || 'record';
        var res_id, value;
        var res_ids = params.res_ids || [];
        var data = params.data || (type === 'record' ? {} : []);
        var context = params.context;
        var fields = Object.assign({
            display_name: {type: 'char'},
            id: {type: 'integer'},
        }, params.fields);

        const groupedBy = params.groupedBy || [];
        let isM2MGrouped = false;
        if (type === 'record') {
            res_id = params.res_id || (params.data && params.data.id);
            if (res_id) {
                data.id = res_id;
            } else {
                res_id = uniqueId('virtual_');
            }
            // it doesn't make sense for a record datapoint to have those keys
            // besides, it will mess up x2m and actions down the line
            context = omit(context, 'orderedBy', 'group_by');
        } else {
            var isValueArray = params.value instanceof Array;
            res_id = isValueArray ? params.value[0] : undefined;
            value = isValueArray ? params.value[1] : params.value;
            isM2MGrouped = groupedBy.some((group) => {
                const [fieldName] = group.split(':');
                return fields[fieldName].type === "many2many";
            });
        }

        var dataPoint = {
            _cache: type === 'list' ? {} : undefined,
            _changes: null,
            _domains: {},
            _rawChanges: {},
            aggregateValues: params.aggregateValues || {},
            context: context,
            count: params.count || res_ids.length,
            data: data,
            domain: params.domain || [],
            fields: fields,
            fieldsInfo: params.fieldsInfo,
            groupedBy,
            groupsCount: 0,
            groupsLimit: type === 'list' && params.groupsLimit || null,
            groupsOffset: 0,
            id: `${params.modelName}_${++this.__id}`,
            isM2MGrouped,
            isOpen: params.isOpen,
            limit: type === 'record' ? 1 : (params.limit || Number.MAX_SAFE_INTEGER),
            loadMoreOffset: 0,
            model: params.modelName,
            offset: params.offset || (type === 'record' ? res_ids.indexOf(res_id) : 0),
            openGroupByDefault: params.openGroupByDefault,
            orderedBy: params.orderedBy || [],
            orderedResIDs: params.orderedResIDs,
            parentID: params.parentID,
            rawContext: params.rawContext,
            ref: params.ref || res_id,
            relationField: params.relationField,
            res_id: res_id,
            res_ids: res_ids,
            specialData: {},
            _specialDataCache: {},
            static: params.static || false,
            type: type,  // 'record' | 'list'
            value: value,
            range: params.range,
            viewType: params.viewType,
        };

        // _editionViewType is a dict whose keys are field names and which is populated when a field
        // is edited with the viewType as value. This is useful for one2manys to determine whether
        // or not a field is readonly (using the readonly modifiers of the view in which the field
        // has been edited)
        dataPoint._editionViewType = {};

        dataPoint.evalModifiers = this._evalModifiers.bind(this, dataPoint);
        dataPoint.getContext = this._getContext.bind(this, dataPoint);
        dataPoint.getDomain = this._getDomain.bind(this, dataPoint);
        dataPoint.getFieldNames = this._getFieldNames.bind(this, dataPoint);
        dataPoint.isDirty = this.isDirty.bind(this, dataPoint.id);
        dataPoint.isNew = this.isNew.bind(this, dataPoint.id);

        this.localData[dataPoint.id] = dataPoint;

        return dataPoint;
    },
    /**
     * When one needs to create a record from scratch, a not so simple process
     * needs to be done:
     * - call the /default_get route to get default values
     * - fetch all relational data
     * - apply all onchanges if necessary
     * - fetch all relational data
     *
     * This method tries to optimize the process as much as possible.  Also,
     * it is quite horrible and should be refactored at some point.
     *
     * @private
     * @param {any} params
     * @param {string} modelName model name
     * @param {boolean} [params.allowWarning=false] if true, the default record
     *   operation can complete, even if a warning is raised
     * @param {Object} params.context the context for the new record
     * @param {Object} params.fieldsInfo contains the fieldInfo of each view,
     *   for each field
     * @param {Object} params.fields contains the description of each field
     * @param {Object} params.context the context for the new record
     * @param {string} params.viewType the key in fieldsInfo of the fields to load
     * @returns {Promise<string>} resolves to the id for the created resource
     */
    async _makeDefaultRecord(modelName, params) {
        var targetView = params.viewType;
        var fields = params.fields;
        var fieldsInfo = params.fieldsInfo;
        var fieldNames = Object.keys(fieldsInfo[targetView]);

        // Fields that are present in the originating view, that need to be initialized
        // Hence preventing their value to crash when getting back to the originating view
        var parentRecord = params.parentID && this.localData[params.parentID].type === 'list' ? this.localData[params.parentID] : null;

        if (parentRecord && parentRecord.viewType in parentRecord.fieldsInfo) {
            var originView = parentRecord.viewType;
            fieldNames = fieldNames.concat(Object.keys(parentRecord.fieldsInfo[originView]));
            fieldsInfo[targetView] = Object.assign({}, parentRecord.fieldsInfo[originView], fieldsInfo[targetView]);
            fields = Object.assign({}, parentRecord.fields, fields);
        }

        var record = this._makeDataPoint({
            modelName: modelName,
            fields: fields,
            fieldsInfo: fieldsInfo,
            context: params.context,
            parentID: params.parentID,
            res_ids: params.res_ids,
            viewType: targetView,
        });

        await this.generateDefaultValues(record.id, {}, { fieldNames });
        try {
            await this._performOnChange(record, [], { firstOnChange: true });
        } finally {
            if (record._warning && params.allowWarning) {
                delete record._warning;
            }
        }
        if (record._warning) {
            return Promise.reject();
        }

        // We want to overwrite the default value of the handle field (if any),
        // in order for new lines to be added at the correct position.
        // -> This is a rare case where the defaul_get from the server
        //    will be ignored by the view for a certain field (usually "sequence").
        var overrideDefaultFields = this._computeOverrideDefaultFields(params.parentID, params.position);
        if (overrideDefaultFields.field) {
            record._changes[overrideDefaultFields.field] = overrideDefaultFields.value;
        }

        // fetch additional data (special data and many2one namegets for "always_reload" fields)
        await this._postprocess(record);
        // save initial changes, so they can be restored later, if we need to discard
        this.save(record.id, { savePoint: true });
        return record.id;
    },
    /**
     * parse the server values to javascript framwork
     *
     * @param {[string]} fieldNames
     * @param {Object} element the dataPoint used as parent for the created
     *   dataPoints
     * @param {Object} data the server data to parse
     */
    _parseServerData: function (fieldNames, element, data) {
        var self = this;
        fieldNames.forEach((fieldName) => {
            var field = element.fields[fieldName];
            var val = data[fieldName];
            if (field.type === 'many2one') {
                // process many2one: split [id, nameget] and create corresponding record
                if (val !== false) {
                    // the many2one value is of the form [id, display_name]
                    var r = self._makeDataPoint({
                        modelName: field.relation,
                        fields: {
                            display_name: {type: 'char'},
                            id: {type: 'integer'},
                        },
                        data: {
                            display_name: val[1],
                            id: val[0],
                        },
                        parentID: element.id,
                    });
                    data[fieldName] = r.id;
                } else {
                    // no value for the many2one
                    data[fieldName] = false;
                }
            } else {
                data[fieldName] = self._parseServerValue(field, val);
            }
        });
    },
    /**
     * This method is quite important: it is supposed to perform the /onchange
     * rpc and apply the result.
     *
     * The changes that triggered the onchange are assumed to have already been
     * applied to the record.
     *
     * @param {Object} record
     * @param {string[]} fields changed fields (empty list in the case of first
     *   onchange)
     * @param {Object} [options={}]
     * @param {string} [options.viewType] current viewType. If not set, we will assume
     *   main viewType from the record
     * @param {boolean} [options.firstOnChange=false] set to true if this is the
     *   first onchange
     * @returns {Promise}
     */
    async _performOnChange(record, fields, options = {}) {
        const firstOnChange = options.firstOnChange;
        let { hasOnchange, onchangeSpec } = this._buildOnchangeSpecs(record, options.viewType);
        if (!firstOnChange && !hasOnchange) {
            return;
        }
        var idList = record.data.id ? [record.data.id] : [];
        const ctxOptions = {
            full: true,
        };
        if (fields.length === 1) {
            fields = fields[0];
            // if only one field changed, add its context to the RPC context
            ctxOptions.fieldName = fields;
        }
        var context = this._getContext(record, ctxOptions);
        var currentData = this._generateOnChangeData(record, {
            changesOnly: false,
            firstOnChange,
        });

        const result = await this._rpc({
            model: record.model,
            method: 'onchange',
            args: [idList, currentData, fields, onchangeSpec],
            context: context,
        });
        if (!record._changes) {
            // if the _changes key does not exist anymore, it means that
            // it was removed by discarding the changes after the rpc
            // to onchange. So, in that case, the proper response is to
            // ignore the onchange.
            return;
        }
        if (result.warning) {
            this.trigger_up('warning', result.warning);
            record._warning = true;
        }
        if (result.domain) {
            record._domains = Object.assign(record._domains, result.domain);
        }
        await this._applyOnChange(result.value, record, { firstOnChange });
        return result;
    },
    /**
     * This function accumulates RPC requests done in the same call stack, and
     * performs them in the next micro task tick so that similar requests can be
     * batched in a single RPC.
     *
     * For now, only 'read' calls are supported.
     *
     * @private
     * @param {Object} params
     * @returns {Promise}
     */
    _performRPC: function (params) {
        var self = this;

        // save the RPC request
        var request = Object.assign({}, params);
        var prom = new Promise(function (resolve, reject) {
            request.resolve = resolve;
            request.reject = reject;
        });
        this.batchedRPCsRequests.push(request);

        // empty the pool of RPC requests in the next micro tick
        Promise.resolve().then(function () {
            if (!self.batchedRPCsRequests.length) {
                // pool has already been processed
                return;
            }

            // reset pool of RPC requests
            var batchedRPCsRequests = self.batchedRPCsRequests;
            self.batchedRPCsRequests = [];

            // batch similar requests
            var batches = {};
            var key;
            for (var i = 0; i < batchedRPCsRequests.length; i++) {
                var request = batchedRPCsRequests[i];
                key = request.model + ',' + JSON.stringify(request.context);
                if (!batches[key]) {
                    batches[key] = Object.assign({}, request, {requests: [request]});
                } else {
                    batches[key].ids = unique(batches[key].ids.concat(request.ids));
                    batches[key].fieldNames = unique(batches[key].fieldNames.concat(request.fieldNames));
                    batches[key].requests.push(request);
                }
            }

            // perform batched RPCs
            function onSuccess(batch, results) {
                for (var i = 0; i < batch.requests.length; i++) {
                    var request = batch.requests[i];
                    var fieldNames = request.fieldNames.concat(['id']);
                    var filteredResults = results.filter(function (record) {
                        return request.ids.indexOf(record.id) >= 0;
                    }).map(function (record) {
                        return pick(record, ...fieldNames);
                    });
                    request.resolve(filteredResults);
                }
            }
            function onFailure(batch, error) {
                for (var i = 0; i < batch.requests.length; i++) {
                    var request = batch.requests[i];
                    request.reject(error);
                }
            }
            for (key in batches) {
                var batch = batches[key];
                self._rpc({
                    model: batch.model,
                    method: 'read',
                    args: [batch.ids, batch.fieldNames],
                    context: batch.context,
                }).then(onSuccess.bind(null, batch)).guardedCatch(onFailure.bind(null, batch));
            }
        });

        return prom;
    },
    /**
     * Once a record is created and some data has been fetched, we need to do
     * quite a lot of computations to determine what needs to be fetched. This
     * method is doing that.
     *
     * @see _fetchRecord @see _makeDefaultRecord
     *
     * @param {Object} record
     * @param {Object} [options]
     * @param {Object} [options.viewType] current viewType. If not set, we will
     *   assume main viewType from the record
     * @returns {Promise<Object>} resolves to the finished resource
     */
    _postprocess: function (record, options) {
        var self = this;
        var viewType = options && options.viewType || record.viewType;
        var defs = [];

        record.getFieldNames(options).forEach((name) => {
            var field = record.fields[name];
            var fieldInfo = record.fieldsInfo[viewType][name] || {};
            var options = fieldInfo.options || {};
            if (options.always_reload) {
                if (record.fields[name].type === 'many2one') {
                    const _changes = record._changes || {};
                    const relRecordId = _changes[name] || record.data[name];
                    if (!relRecordId) {
                        return; // field is unset, no need to do the display_name read
                    }
                    var relRecord = self.localData[relRecordId];
                    defs.push(self._rpc({
                            model: field.relation,
                            method: 'read',
                            args: [relRecord.data.id, ['display_name']],
                            context: self._getContext(record, {fieldName: name, viewType: viewType, withoutRecordData: true}),
                        })
                        .then(function (result) {
                            relRecord.data.display_name = result[0]['display_name'];
                        }));
                }
            }
        });

        defs.push(this._fetchSpecialData(record, options));

        return Promise.all(defs).then(function () {
            record._specialDataSavepoint = Object.assign({}, record.specialData);
            return record;
        });
    },
    /**
     * Process x2many commands in a default record by transforming the list of
     * commands in operations (pushed in _changes) and fetch the related
     * records fields.
     *
     * Note that this method can be called recursively.
     *
     * @todo in master: factorize this code with the postprocessing of x2many in
     *  _applyOnChange
     *
     * @private
     * @param {Object} record
     * @param {string} fieldName
     * @param {Array[Array]} commands
     * @param {Object} [options]
     * @param {string} [options.viewType] current viewType. If not set, we will
     *   assume main viewType from the record
     * @returns {Promise}
     */
    _processX2ManyCommands: function (record, fieldName, commands, options) {
        var self = this;
        options = options || {};
        var defs = [];
        var field = record.fields[fieldName];
        var fieldInfo = record.fieldsInfo[options.viewType || record.viewType][fieldName] || {};
        var view = fieldInfo.views && fieldInfo.views[fieldInfo.mode];
        var fieldsInfo = view ? view.fieldsInfo : fieldInfo.fieldsInfo;
        var fields = view ? view.fields : fieldInfo.relatedFields;
        var viewType = view ? view.type : fieldInfo.viewType;

        // remove default_* & *_view_ref keys from record context
        const recordContext = { ...record.context };
        for (const key in recordContext) {
            if (key.startsWith("default_") || key.endsWith("_view_ref")) {
                delete recordContext[key];
            }
        }

        var x2manyList = self._makeDataPoint({
            context: recordContext,
            fieldsInfo: fieldsInfo,
            fields: fields,
            limit: fieldInfo.limit,
            modelName: field.relation,
            parentID: record.id,
            rawContext: fieldInfo && fieldInfo.context,
            relationField: field.relation_field,
            res_ids: [],
            static: true,
            type: 'list',
            viewType: viewType,
        });
        record._changes[fieldName] = x2manyList.id;
        x2manyList._changes = [];
        var many2ones = {};
        var r;
        commands = commands || []; // handle false value
        var isCommandList = commands.length && Array.isArray(commands[0]);
        if (!isCommandList) {
            commands = [[6, false, commands]];
        }
        commands.forEach((value) => {
            // value is a command
            if (value[0] === 0) {
                // CREATE
                r = self._makeDataPoint({
                    modelName: x2manyList.model,
                    context: x2manyList.context,
                    fieldsInfo: fieldsInfo,
                    fields: fields,
                    parentID: x2manyList.id,
                    viewType: viewType,
                });
                r._noAbandon = true;
                x2manyList._changes.push({operation: 'ADD', id: r.id});
                x2manyList._cache[r.res_id] = r.id;

                // this is necessary so the fields are initialized
                r.getFieldNames().forEach((fieldName) => {
                    r.data[fieldName] = null;
                });

                r._changes = Object.assign(r.data, value[2]);
                for (var fieldName in r._changes) {
                    if (!r._changes[fieldName]) {
                        continue;
                    }
                    var isFieldInView = fieldName in r.fields;
                    if (isFieldInView) {
                        var field = r.fields[fieldName];
                        var fieldType = field.type;
                        var rec;
                        if (fieldType === 'many2one') {
                            rec = self._makeDataPoint({
                                context: r.context,
                                modelName: field.relation,
                                data: {id: r._changes[fieldName]},
                                parentID: r.id,
                            });
                            r._changes[fieldName] = rec.id;
                            many2ones[fieldName] = true;
                        } else if (fieldType === 'reference') {
                            var reference = r._changes[fieldName].split(',');
                            rec = self._makeDataPoint({
                                context: r.context,
                                modelName: reference[0],
                                data: {id: parseInt(reference[1])},
                                parentID: r.id,
                            });
                            r._changes[fieldName] = rec.id;
                            many2ones[fieldName] = true;
                        } else if (['one2many', 'many2many'].includes(fieldType)) {
                            var x2mCommands = value[2][fieldName];
                            defs.push(self._processX2ManyCommands(r, fieldName, x2mCommands));
                        } else {
                            r._changes[fieldName] = self._parseServerValue(field, r._changes[fieldName]);
                        }
                    }
                }
            }
            if (value[0] === 6) {
                // REPLACE_WITH
                value[2].forEach((res_id) => {
                    x2manyList._changes.push({operation: 'ADD', resID: res_id});
                });
                var def = self._readUngroupedList(x2manyList).then(function () {
                    return Promise.all([
                        self._fetchX2ManysBatched(x2manyList),
                        self._fetchReferencesBatched(x2manyList)
                    ]);
                });
                defs.push(def);
            }
        });

        // fetch many2ones display_name
        Object.keys(many2ones).forEach((name) => {
            defs.push(self._fetchNameGets(x2manyList, name));
        });

        return Promise.all(defs);
    },
    /**
     * Reads data from server for all missing fields.
     *
     * @private
     * @param {Object} list a valid resource object
     * @param {interger[]} resIDs
     * @param {string[]} fieldNames to check and read if missing
     * @returns {Promise<Object>}
     */
    _readMissingFields: function (list, resIDs, fieldNames, withoutRecordData) {
        var self = this;

        var missingIDs = [];
        for (var i = 0, len = resIDs.length; i < len; i++) {
            var resId = resIDs[i];
            var dataPointID = list._cache[resId];
            if (!dataPointID) {
                missingIDs.push(resId);
                continue;
            }
            var record = self.localData[dataPointID];
            var data = Object.assign({}, record.data, record._changes);
            if (fieldNames.filter((x) => Object.keys(data).indexOf(x) < 0).length) {
                missingIDs.push(resId);
            }
        }

        var def;
        if (missingIDs.length && fieldNames.length) {
            def = self._performRPC({
                context: list.getContext({ withoutRecordData: !!withoutRecordData }),
                fieldNames: fieldNames,
                ids: missingIDs,
                method: 'read',
                model: list.model,
            });
        } else {
            def = Promise.resolve(missingIDs.map((id) => {
                return {id:id};
            }));
        }
        return def.then(function (records) {
            resIDs.forEach((id) => {
                var dataPoint;
                var data = records.find((record) => record.id === id);
                if (id in list._cache) {
                    dataPoint = self.localData[list._cache[id]];
                    if (data) {
                        self._parseServerData(fieldNames, dataPoint, data);
                        Object.assign(dataPoint.data, data);
                    }
                } else {
                    dataPoint = self._makeDataPoint({
                        context: list.getContext(),
                        data: data,
                        fieldsInfo: list.fieldsInfo,
                        fields: list.fields,
                        modelName: list.model,
                        parentID: list.id,
                        viewType: list.viewType,
                    });
                    self._parseServerData(fieldNames, dataPoint, dataPoint.data);

                    // add many2one records
                    list._cache[id] = dataPoint.id;
                }
                // set the dataPoint id in potential 'ADD' operation adding the current record
                Object.values(list._changes || {}).forEach((change) => {
                    if (change.operation === 'ADD' && !change.id && change.resID === id) {
                        change.id = dataPoint.id;
                    }
                });
            });
            return list;
        });
    },
    /**
     * For a grouped list resource, this method fetches all group data by
     * performing a /read_group. It also tries to read open subgroups if they
     * were open before.
     *
     * @param {Object} list valid resource object
     * @param {Object} [options] @see _load
     * @returns {Promise<Object>} resolves to the fetched group object
     */
    _readGroup: function (list, options) {
        var self = this;
        options = options || {};
        var groupByField = list.groupedBy[0];
        var rawGroupBy = groupByField.split(':')[0];
        var fields = unique(list.getFieldNames().concat(rawGroupBy));
        var orderedBy = list.orderedBy?.filter(order => {
            return order.name === rawGroupBy || list.fields[order.name].group_operator !== undefined;
        }) || [];
        var openGroupsLimit = list.groupsLimit || self.OPEN_GROUP_LIMIT;
        var expand = list.openGroupByDefault && options.fetchRecordsWithGroups;
        return this._rpc({
                model: list.model,
                method: 'web_read_group',
                fields: fields,
                domain: list.domain,
                context: list.context,
                groupBy: list.groupedBy,
                limit: list.groupsLimit,
                offset: list.groupsOffset,
                orderBy: orderedBy,
                lazy: true,
                expand: expand,
                expand_limit: expand ? list.limit : null,
                expand_orderby: expand ? list.orderedBy : null,
            })
            .then(function (result) {
                var groups = result.groups;
                list.groupsCount = result.length;
                var previousGroups = list.data.map((groupID) => self.localData[groupID]);
                list.data = [];
                list.count = 0;
                var defs = [];
                var openGroupCount = 0;

                groups.forEach((group) => {
                    var aggregateValues = {};
                    for (const [key, value] of Object.entries(group)) {
                        if (fields.includes(key) && key !== groupByField &&
                            AGGREGATABLE_TYPES.includes(list.fields[key].type)) {
                                aggregateValues[key] = value;
                        }
                    }
                    // When a view is grouped, we need to display the name of each group in
                    // the 'title'.
                    var value = group[groupByField];
                    if (list.fields[rawGroupBy].type === "selection") {
                        var choice = list.fields[rawGroupBy].selection.find(c => c[0] === value);
                        value = choice ? choice[1] : false;
                    }
                    var newGroup = self._makeDataPoint({
                        modelName: list.model,
                        count: group[rawGroupBy + '_count'],
                        domain: group.__domain,
                        context: list.context,
                        fields: list.fields,
                        fieldsInfo: list.fieldsInfo,
                        value: value,
                        range: group.__range,
                        aggregateValues: aggregateValues,
                        groupedBy: list.groupedBy.slice(1),
                        orderedBy: list.orderedBy,
                        orderedResIDs: list.orderedResIDs,
                        limit: list.limit,
                        openGroupByDefault: list.openGroupByDefault,
                        parentID: list.id,
                        type: 'list',
                        viewType: list.viewType,
                    });
                    var oldGroup = previousGroups.find(g => g.res_id === newGroup.res_id && g.value === newGroup.value);
                    if (oldGroup) {
                        delete self.localData[newGroup.id];
                        // restore the internal state of the group
                        const oldPropsToKeep = self._getGroupedListPropsToKeep(oldGroup, {
                            onlyGroup: options.onlyGroups,
                            hasSubgroups: newGroup.groupedBy.length
                        });
                        Object.assign(newGroup, oldPropsToKeep);
                        // set the limit such that all previously loaded records
                        // (e.g. if we are coming back to the kanban view from a
                        // form view) are reloaded
                        newGroup.limit = oldGroup.limit + oldGroup.loadMoreOffset;
                        self.localData[newGroup.id] = newGroup;
                    } else if (!newGroup.openGroupByDefault || openGroupCount >= openGroupsLimit) {
                        newGroup.isOpen = false;
                    } else if ('__fold' in group) {
                        newGroup.isOpen = !group.__fold;
                    } else {
                        // open the group iff it is a first level group
                        newGroup.isOpen = !self.localData[newGroup.parentID].parentID;
                    }
                    list.data.push(newGroup.id);
                    list.count += newGroup.count;
                    if (newGroup.isOpen && newGroup.count > 0) {
                        openGroupCount++;
                        if (group.__data) {
                            // bypass the search_read when the group's records have been obtained
                            // by the call to 'web_read_group' (see @_searchReadUngroupedList)
                            newGroup.__data = group.__data;
                        }
                        options = Object.assign(options, {enableRelationalFetch: false});
                        defs.push(self._load(newGroup, options));
                    }
                });
                if (options.keepEmptyGroups) {
                    // Find the groups that were available in a previous
                    // readGroup but are not there anymore.
                    // Note that these groups are put after existing groups so
                    // the order is not conserved. A sort *might* be useful.
                    var emptyGroupsIDs = previousGroups.map((group) => group.id).filter((x) => list.data.indexOf(x)<0);
                    emptyGroupsIDs.forEach((groupID) => {
                        list.data.push(groupID);
                        var emptyGroup = self.localData[groupID];
                        // this attribute hasn't been updated in the previous
                        // loop for empty groups
                        emptyGroup.aggregateValues = {};
                    });
                }

                return Promise.all(defs).then(function (groups) {
                    if (!options.onlyGroups) {
                        // generate the res_ids of the main list, being the concatenation
                        // of the fetched res_ids in each group
                        list.res_ids = groups.map((group) => {
                            return group ? group.res_ids : [];
                        }).flat();
                    }
                    return list;
                }).then(function () {
                    return Promise.all([
                        self._fetchX2ManysSingleBatch(list),
                        self._fetchReferencesSingleBatch(list)
                    ]).then(function () {
                        return list;
                    });
                });
            });
    },
    /**
     * For 'static' list, such as one2manys in a form view, we can do a /read
     * instead of a /search_read.
     *
     * @param {Object} list a valid resource object
     * @returns {Promise<Object>} resolves to the fetched list object
     */
    _readUngroupedList: function (list, options) {
        options = options || {};
        var self = this;
        var def = Promise.resolve();

        // generate the current count and res_ids list by applying the changes
        list = this._applyX2ManyOperations(list);

        // for multi-pages list datapoints, we might need to read the
        // order field first to apply the order on all pages
        if (list.res_ids.length > list.limit && list.orderedBy.length) {
            if (!list.orderedResIDs) {
                var fieldNames = list.orderedBy.map((list) => list.name);
                def = this._readMissingFields(list, list.res_ids.filter(id => Number.isFinite(id)), fieldNames, options.withoutRecordData);
            }
            def.then(function () {
                self._sortList(list);
            });
        }
        return def.then(function () {
            var resIDs = [];
            var currentResIDs = list.res_ids;
            // if new records have been added to the list, their virtual ids have
            // been pushed at the end of res_ids (or at the beginning, depending
            // on the editable property), ignoring completely the current page
            // where the records have actually been created ; for that reason,
            // we use orderedResIDs which is a freezed order with the virtual ids
            // at the correct position where they were actually inserted ; however,
            // when we use orderedResIDs, we must filter out ids that are not in
            // res_ids, which correspond to records that have been removed from
            // the relation (this information being taken into account in res_ids
            // but not in orderedResIDs)
            if (list.orderedResIDs) {
                currentResIDs = list.orderedResIDs.filter(function (resID) {
                    return list.res_ids.indexOf(resID) >= 0;
                });
            }
            var currentCount = currentResIDs.length;
            var upperBound = list.limit ? Math.min(list.offset + list.limit, currentCount) : currentCount;
            var fieldNames = list.getFieldNames();
            for (var i = list.offset; i < upperBound; i++) {
                var resId = currentResIDs[i];
                if (Number.isFinite(resId)) {
                    resIDs.push(resId);
                }
            }
            return self._readMissingFields(list, resIDs, fieldNames, options.withoutRecordData).then(function () {
                if (list.res_ids.length <= list.limit) {
                    self._sortList(list);
                } else {
                    // sortList has already been applied after first the read
                    self._setDataInRange(list);
                }
                return list;
            });
        });
    },
    /**
     * Reload all data for a given resource
     *
     * @private
     * @param {string} id local id for a resource
     * @param {Object} [options]
     * @param {boolean} [options.keepChanges=false] if true, doesn't discard the
     *   changes on the record before reloading it
     * @returns {Promise<string>} resolves to the id of the resource
     */
    _reload: function (id, options) {
        options = options || {};
        var element = this.localData[id];

        if (element.type === 'record') {
            if (!options.currentId && (('currentId' in options) || this.isNew(id))) {
                var params = {
                    context: element.context,
                    fieldsInfo: element.fieldsInfo,
                    fields: element.fields,
                    viewType: element.viewType,
                    allowWarning: true,
                };
                return this._makeDefaultRecord(element.model, params);
            }
            if (!options.keepChanges) {
                this.discardChanges(id, {rollback: false});
            }
        } else if (element._changes) {
            delete element.tempLimitIncrement;
            element._changes.forEach((change) => {
                delete change.isNew;
            });
        }

        if (options.context !== undefined) {
            element.context = options.context;
        }
        if (options.orderedBy !== undefined) {
            element.orderedBy = (options.orderedBy.length && options.orderedBy) || element.orderedBy;
        }
        if (options.domain !== undefined) {
            element.domain = options.domain;
        }
        if (options.groupBy !== undefined) {
            element.groupedBy = options.groupBy;
            element.isM2MGrouped = element.groupedBy.some((group) => {
                const [fieldName] = group.split(':');
                return element.fields[fieldName].type === "many2many";
            });
        }
        if (options.limit !== undefined) {
            element.limit = options.limit;
        }
        if (options.offset !== undefined) {
            this._setOffset(element.id, options.offset);
        }
        if (options.groupsLimit !== undefined) {
            element.groupsLimit = options.groupsLimit;
        }
        if (options.groupsOffset !== undefined) {
            element.groupsOffset = options.groupsOffset;
        }
        if (options.loadMoreOffset !== undefined) {
            element.loadMoreOffset = options.loadMoreOffset;
        } else {
            // reset if not specified
            element.loadMoreOffset = 0;
        }
        if (options.currentId !== undefined) {
            element.res_id = options.currentId;
        }
        if (options.ids !== undefined) {
            element.res_ids = options.ids;
            element.count = element.res_ids.length;
        }
        if (element.type === 'record') {
            element.offset = element.res_ids.indexOf(element.res_id);
        }
        var loadOptions = pick(options, 'fieldNames', 'viewType');
        return this._load(element, loadOptions).then(function (result) {
            return result.id;
        });
    },
    /**
     * Override to handle the case where we want sample data, and we are in a
     * grouped kanban or list view with real groups, but all groups are empty.
     * In this case, we use the result of the web_read_group rpc to tweak the
     * data in the SampleServer instance of the sampleModel (so that calls to
     * that server will return the same groups).
     *
     * @override
     */
    async _rpc(params) {
        const result = await this._super(...arguments);
        if (this.sampleModel && params.method === 'web_read_group' && result.length) {
            const sampleServer = this.sampleModel.sampleServer;
            sampleServer.setExistingGroups(result.groups);
        }
        return result;
    },
    /**
     * Allows to save a value in the specialData cache associated to a given
     * record and fieldName. If the value in the cache was already the given
     * one, nothing is done and the method indicates it by returning false
     * instead of true.
     *
     * @private
     * @param {Object} record - an element from the localData
     * @param {string} fieldName - the name of the field
     * @param {*} value - the cache value to save
     * @returns {boolean} false if the value was already the given one
     */
    _saveSpecialDataCache: function (record, fieldName, value) {
        if (JSON.stringify(record._specialDataCache[fieldName]) === JSON.stringify(value)) {
            return false;
        }
        record._specialDataCache[fieldName] = value;
        return true;
    },
    /**
     * Do a /search_read to get data for a list resource.  This does a
     * /search_read because the data may not be static (for ex, a list view).
     *
     * @param {Object} list
     * @returns {Promise}
     */
    _searchReadUngroupedList: function (list) {
        var self = this;
        var fieldNames = list.getFieldNames();
        var prom;
        if (list.__data) {
            // the data have already been fetched (alongside the groups by the
            // call to 'web_read_group'), so we can bypass the search_read
            // But the web_read_group returns the rawGroupBy field's value, which may not be present
            // in the view. So we filter it out.
            const fieldNameSet = new Set(fieldNames);
            fieldNameSet.add("id"); // don't filter out the id
            list.__data.records.forEach(record =>
                Object.keys(record)
                    .filter(fieldName => !fieldNameSet.has(fieldName))
                    .forEach(fieldName => delete record[fieldName]));
            prom = Promise.resolve(list.__data);
        } else {
            prom = this._rpc({
                route: '/web/dataset/search_read',
                model: list.model,
                fields: fieldNames,
                context: Object.assign({}, list.getContext(), {bin_size: true}),
                domain: this._getUngroupedListDomain(list),
                limit: list.limit,
                offset: list.loadMoreOffset + list.offset,
                orderBy: list.orderedBy,
            });
        }
        return prom.then(function (result) {
            delete list.__data;
            list.count = result.length;
            var ids = result.records.map((r) => r.id);
            var data = result.records.map((record) => {
                var dataPoint = self._makeDataPoint({
                    context: list.context,
                    data: record,
                    fields: list.fields,
                    fieldsInfo: list.fieldsInfo,
                    modelName: list.model,
                    parentID: list.id,
                    viewType: list.viewType,
                });

                // add many2one records
                self._parseServerData(fieldNames, dataPoint, dataPoint.data);
                return dataPoint.id;
            });
            if (list.loadMoreOffset) {
                list.data = list.data.concat(data);
                list.res_ids = list.res_ids.concat(ids);
            } else {
                list.data = data;
                list.res_ids = ids;
            }
            self._updateParentResIDs(list);
            return list;
        });
    },
    /**
     * Set data in range, i.e. according to the list offset and limit.
     *
     * @param {Object} list
     */
    _setDataInRange: function (list) {
        var idsInRange;
        if (list.limit) {
            idsInRange = list.res_ids.slice(list.offset, list.offset + list.limit);
        } else {
            idsInRange = list.res_ids;
        }
        list.data = [];
        idsInRange.forEach((id) => {
            if (list._cache[id]) {
                list.data.push(list._cache[id]);
            }
        });

        // display newly created record in addition to the displayed records
        if (list.limit) {
            for (var i = list.offset + list.limit; i < list.res_ids.length; i++) {
                var id = list.res_ids[i];
                var dataPointID = list._cache[id];
                if (Object.values(list._changes || {}).find((change) => change.isNew === true && change.id === dataPointID)) {
                    list.data.push(dataPointID);
                } else {
                    break;
                }
            }
        }
    },
    /**
     * Change the offset of a record. Note that this does not reload the data.
     * The offset is used to load a different record in a list of record (for
     * example, a form view with a pager.  Clicking on next/previous actually
     * changes the offset through this method).
     *
     * @param {string} elementId local id for the resource
     * @param {number} offset
     */
    _setOffset: function (elementId, offset) {
        var element = this.localData[elementId];
        element.offset = offset;
        if (element.type === 'record' && element.res_ids.length) {
            element.res_id = element.res_ids[offset];
        }
    },
    /**
     * Do a in-memory sort of a list resource data points. This method assumes
     * that the list data has already been fetched, and that the changes that
     * need to be sorted have already been applied. Its intended use is for
     * static datasets, such as a one2many in a form view.
     *
     * @param {Object} list list dataPoint on which (some) changes might have
     *   been applied; it is a copy of an internal dataPoint, not the result of
     *   get
     */
    _sortList: function (list) {
        if (!list.static) {
            // only sort x2many lists
            return;
        }
        var self = this;

        if (list.orderedResIDs) {
            var orderedResIDs = {};
            for (var k = 0; k < list.orderedResIDs.length; k++) {
                orderedResIDs[list.orderedResIDs[k]] = k;
            }
            utils.stableSort(list.res_ids, function compareResIdIndexes (resId1, resId2) {
                if (!(resId1 in orderedResIDs) && !(resId2 in orderedResIDs)) {
                    return 0;
                }
                if (!(resId1 in orderedResIDs)) {
                    return Infinity;
                }
                if (!(resId2 in orderedResIDs)) {
                    return -Infinity;
                }
                return orderedResIDs[resId1] - orderedResIDs[resId2];
            });
        } else if (list.orderedBy.length) {
            // sort records according to ordered_by[0]
            var compareRecords = function (resId1, resId2, level) {
                if(!level) {
                    level = 0;
                }
                if(list.orderedBy.length < level + 1) {
                    return 0;
                }
                var order = list.orderedBy[level];
                var record1ID = list._cache[resId1];
                var record2ID = list._cache[resId2];
                if (!record1ID && !record2ID) {
                    return 0;
                }
                if (!record1ID) {
                    return Infinity;
                }
                if (!record2ID) {
                    return -Infinity;
                }
                var r1 = self.localData[record1ID];
                var r2 = self.localData[record2ID];
                var data1 = Object.assign({}, r1.data, r1._changes);
                var data2 = Object.assign({}, r2.data, r2._changes);

                // Default value to sort against: the value of the field
                var orderData1 = data1[order.name];
                var orderData2 = data2[order.name];

                // If the field is a relation, sort on the display_name of those records
                if (list.fields[order.name].type === 'many2one') {
                    orderData1 = orderData1 ? self.localData[orderData1].data.display_name : "";
                    orderData2 = orderData2 ? self.localData[orderData2].data.display_name : "";
                }
                if (orderData1 < orderData2) {
                    return order.asc ? -1 : 1;
                }
                if (orderData1 > orderData2) {
                    return order.asc ? 1 : -1;
                }
                return compareRecords(resId1, resId2, level + 1);
            };
            utils.stableSort(list.res_ids, compareRecords);
        }
        this._setDataInRange(list);
    },
    /**
     * Updates the res_ids of the parent of a given element of type list.
     *
     * After some operations (e.g. loading more records, folding/unfolding a
     * group), the res_ids list of an element may be updated. When this happens,
     * the res_ids of its ancestors need to be updated as well. This is the
     * purpose of this function.
     *
     * @param {Object} element
     */
    _updateParentResIDs: function (element) {
        var self = this;
        if (element.parentID) {
            var parent = this.localData[element.parentID];
            parent.res_ids =  parent.data.map((dataPointID) => self.localData[dataPointID].res_ids).flat();
            this._updateParentResIDs(parent);
        }
    },
    /**
     * Helper method to create datapoints and assign them values, then link
     * those datapoints into records' data.
     *
     * @param {Object[]} records a list of record where datapoints will be
     *   assigned, it assumes _applyX2ManyOperations and _sort have been
     *   already called on this list
     * @param {string} fieldName concerned field in records
     * @param {Object[]} values typically a list of values got from a rpc
     */
    _updateRecordsData: function (records, fieldName, values) {
        if (!records.length || !values) {
            return;
        }
        var self = this;
        var field = records[0].fields[fieldName];
        var fieldInfo = records[0].fieldsInfo[records[0].viewType][fieldName];
        var view = fieldInfo.views && fieldInfo.views[fieldInfo.mode];
        var fieldsInfo = view ? view.fieldsInfo : fieldInfo.fieldsInfo;
        var fields = view ? view.fields : fieldInfo.relatedFields;
        var viewType = view ? view.type : fieldInfo.viewType;
        var id2Values = new Map(values.map((value) => [value.id, value]))

        records.forEach((record) => {
            var x2mList = self.localData[record.data[fieldName]];
            x2mList.data = [];
            x2mList.res_ids.forEach((res_id) => {
                var dataPoint = self._makeDataPoint({
                    modelName: field.relation,
                    data: id2Values.get(res_id),
                    fields: fields,
                    fieldsInfo: fieldsInfo,
                    parentID: x2mList.id,
                    viewType: viewType,
                });
                x2mList.data.push(dataPoint.id);
                x2mList._cache[res_id] = dataPoint.id;
            });
        });
    },
    /**
     * Used to apply a updateFn to other records with same res_id, that are
     * under the same topmost list groupedby many2many.
     *
     * When a list datapoint is grouped by many2many, same res_id record could
     * be in multiple groups, so use this method to apply the same callback to
     * each one of them.
     *
     * @protected
     * @param {string} recordID local resource
     * @param {(recordID: string)=>void} updateFn called for each record datapoint
     *  representing the same res_id record
     */
    _updateDuplicateRecords(recordID, updateFn) {
        const { res_id } = this.localData[recordID];
        // Get the topmost groupedby m2m list
        const getTopmostID = () => {
            let element = this.localData[recordID];
            while (element.parentID && this.localData[element.parentID].type === "list") {
                element = this.localData[element.parentID];
            }
            return element.type === "list" && element.isM2MGrouped ? element.id : false;
        };
        const topmostID = getTopmostID();
        if (!topmostID) {
            return;
        }
        const topmostList = this.get(topmostID);
        utils.traverse_records(topmostList, (r) => {
            if (r.res_id === res_id && r.id !== recordID) {
                updateFn(r.id);
            }
        });
    },
    /**
     * Helper method.  Recursively traverses the data, starting from the element
     * record (or list), then following all relations.  This is useful when one
     * want to determine a property for the current record.
     *
     * For example, isDirty need to check all relations to find out if something
     * has been modified, or not.
     *
     * Note that this method follows all the changes, so if a record has
     * relational sub data, it will visit the new sub records and not the old
     * ones.
     *
     * @param {Object} element a valid local resource
     * @param {callback} fn a function to be called on each visited element
     */
    _visitChildren: function (element, fn) {
        var self = this;
        fn(element);
        if (element.type === 'record') {
            for (var fieldName in element.data) {
                var field = element.fields[fieldName];
                if (!field) {
                    continue;
                }
                if (['one2many', 'many2one', 'many2many'].includes(field.type)) {
                    var hasChange = element._changes && fieldName in element._changes;
                    var value =  hasChange ? element._changes[fieldName] : element.data[fieldName];
                    var relationalElement = this.localData[value];
                    // relationalElement could be empty in the case of a many2one
                    if (relationalElement) {
                        self._visitChildren(relationalElement, fn);
                    }
                }
            }
        }
        if (element.type === 'list') {
            element = this._applyX2ManyOperations(element);
            element.data.forEach((elemId) => {
                var elem = self.localData[elemId];
                self._visitChildren(elem, fn);
            });
        }
    },
});

export default BasicModel;
