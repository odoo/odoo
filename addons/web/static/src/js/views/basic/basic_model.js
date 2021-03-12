odoo.define('web.BasicModel', function (require) {
"use strict";

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

var AbstractModel = require('web.AbstractModel');
var concurrency = require('web.concurrency');
var Context = require('web.Context');
var core = require('web.core');
var Domain = require('web.Domain');
var session = require('web.session');
var utils = require('web.utils');

var _t = core._t;

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

    // list of models for which the DataManager's cache should be cleared on
    // create, update and delete operations
    noCacheModels: [
        'ir.actions.act_window',
        'ir.filters',
        'ir.ui.view',
    ],
    // FORWARDPORT THIS UP TO 12.2, NOT FURTHER
    disableBatchedRPCs: false, // to be overriden in tests

    /**
     * @override
     */
    init: function () {
        // this mutex is necessary to make sure some operations are done
        // sequentially, for example, an onchange needs to be completed before a
        // save is performed.
        this.mutex = new concurrency.Mutex();

        // FORWARDPORT THIS UP TO 12.2, NOT FURTHER
        // this array is used to accumulate RPC requests done in the same call
        // stack, so that they can be batched in the minimum number of RPCs
        this.batchedRPCsRequests = [];

        this.localData = Object.create(null);
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
     * @returns {Deferred<string>} resolves to the id of the new created record
     */
    addDefaultRecord: function (listID, options) {
        var self = this;
        var list = this.localData[listID];
        var context = this._getContext(list);

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
     * Add and process default values for a given record. Those values are
     * parsed and stored in the '_changes' key of the record. For relational
     * fields, sub-dataPoints are created, and missing relational data is
     * fetched. Also generate default values for fields with no given value.
     * Typically, this function is called with the result of a 'default_get'
     * RPC, to populate a newly created dataPoint. It may also be called when a
     * one2many subrecord is open in a form view (dialog), to generate the
     * default values for the fields displayed in the o2m form view, but not in
     * the list or kanban (mainly to correctly create sub-dataPoints for
     * relational fields).
     *
     * @param {string} recordID local id for a record
     * @param {Object} values dict of default values for the given record
     * @param {Object} [options]
     * @param {string} [options.viewType] current viewType. If not set, we will
     *   assume main viewType from the record
     * @param {Array} [options.fieldNames] list of field names for which a
     *   default value must be generated (used to complete the values dict)
     * @returns {Deferred}
     */
    applyDefaultValues: function (recordID, values, options) {
        options = options || {};
        var record = this.localData[recordID];
        var viewType = options.viewType || record.viewType;
        var fieldNames = options.fieldNames || Object.keys(record.fieldsInfo[viewType]);
        var field;
        var fieldName;
        record._changes = record._changes || {};

        // ignore values for non requested fields (for instance, fields that are
        // not in the view)
        values = _.pick(values, fieldNames);

        // fill default values for missing fields
        for (var i = 0; i < fieldNames.length; i++) {
            fieldName = fieldNames[i];
            if (!(fieldName in values) && !(fieldName in record._changes)) {
                field = record.fields[fieldName];
                if (field.type === 'float' ||
                    field.type === 'integer' ||
                    field.type === 'monetary') {
                    values[fieldName] = 0;
                } else if (field.type === 'one2many' || field.type === 'many2many') {
                    values[fieldName] = [];
                } else {
                    values[fieldName] = null;
                }
            }
        }

        // parse each value and create dataPoints for relational fields
        var defs = [];
        for (fieldName in values) {
            field = record.fields[fieldName];
            record.data[fieldName] = null;
            var dp;
            if (field.type === 'many2one' && values[fieldName]) {
                dp = this._makeDataPoint({
                    context: record.context,
                    data: {id: values[fieldName]},
                    modelName: field.relation,
                    parentID: record.id,
                });
                record._changes[fieldName] = dp.id;
            } else if (field.type === 'reference' && values[fieldName]) {
                var ref = values[fieldName].split(',');
                dp = this._makeDataPoint({
                    context: record.context,
                    data: {id: parseInt(ref[1])},
                    modelName: ref[0],
                    parentID: record.id,
                });
                defs.push(this._fetchNameGet(dp));
                record._changes[fieldName] = dp.id;
            } else if (field.type === 'one2many' || field.type === 'many2many') {
                defs.push(this._processX2ManyCommands(record, fieldName, values[fieldName], options));
            } else {
                record._changes[fieldName] = this._parseServerValue(field, values[fieldName]);
            }
        }

        return $.when.apply($, defs);
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
     * @returns {Deferred<string>} resolves to the id of the record
     */
    applyRawChanges: function (recordID, viewType) {
        var record = this.localData[recordID];
        return this._applyOnChange(record._rawChanges, record, viewType).then(function () {
            return record.id;
        });
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
     * @returns {Deferred}
     */
    deleteRecords: function (recordIds, modelName) {
        var self = this;
        var records = _.map(recordIds, function (id) { return self.localData[id]; });
        var context = _.extend(records[0].getContext(), session.user_context);
        return this._rpc({
                model: modelName,
                method: 'unlink',
                args: [_.pluck(records, 'res_id')],
                context: context,
            })
            .then(function () {
                _.each(records, function (record) {
                    var parent = record.parentID && self.localData[record.parentID];
                    if (parent && parent.type === 'list') {
                        parent.data = _.without(parent.data, record.id);
                        delete self.localData[record.id];
                    } else {
                        record.res_ids.splice(record.offset, 1);
                        record.offset = Math.min(record.offset, record.res_ids.length - 1);
                        record.res_id = record.res_ids[record.offset];
                        record.count--;
                    }
                });
                // optionally clear the DataManager's cache
                self._invalidateCache(records[0]);
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
                    elem._changes = _.extend({}, elem._savePoint);
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
        });
        element.offset = initialOffset;
    },
    /**
     * Duplicate a record (by calling the 'copy' route)
     *
     * @param {string} recordID id for a local resource
     * @returns {Deferred<string>} resolves to the id of duplicate record
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
     * The get method first argument is the handle returned by the load method.
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
    get: function (id, options) {
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
            var data = _.extend({}, element.data, element._changes);
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
                        data[fieldName] = this.get(data[fieldName]) || false;
                    }
                } else if (field.type === 'reference') {
                    if (options.raw) {
                        relDataPoint = this.localData[data[fieldName]];
                        data[fieldName] = relDataPoint ?
                            relDataPoint.model + ',' + relDataPoint.res_id :
                            false;
                    } else {
                        data[fieldName] = this.get(data[fieldName]) || false;
                    }
                } else if (field.type === 'one2many' || field.type === 'many2many') {
                    if (options.raw) {
                        relDataPoint = this.localData[data[fieldName]];
                        relDataPoint = this._applyX2ManyOperations(relDataPoint);
                        data[fieldName] = relDataPoint.res_ids;
                    } else {
                        data[fieldName] = this.get(data[fieldName]) || [];
                    }
                }
            }
            var record = {
                context: _.extend({}, element.context),
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
                limit: element.limit,
                model: element.model,
                offset: element.offset,
                ref: element.ref,
                res_ids: element.res_ids.slice(0),
                specialData: _.extend({}, element.specialData),
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
            _.each(element._changes, function (change) {
                if (change.operation === 'ADD' && change.isNew) {
                    element.data = _.without(element.data, change.id);
                    if (change.position === 'top') {
                        element.data.unshift(change.id);
                    } else {
                        element.data.push(change.id);
                    }
                }
            });
        }

        var list = {
            aggregateValues: _.extend({}, element.aggregateValues),
            context: _.extend({}, element.context),
            count: element.count,
            data: _.map(element.data, function (elemID) {
                return self.get(elemID, options);
            }),
            domain: element.domain.slice(0),
            fields: element.fields,
            getContext: element.getContext,
            getDomain: element.getDomain,
            getFieldNames: element.getFieldNames,
            groupedBy: element.groupedBy,
            id: element.id,
            isDirty: element.isDirty,
            isOpen: element.isOpen,
            limit: element.limit,
            model: element.model,
            offset: element.offset,
            orderedBy: element.orderedBy,
            res_id: element.res_id,
            res_ids: element.res_ids.slice(0),
            type: 'list',
            value: element.value,
            viewType: element.viewType,
        };
        if (element.fieldsInfo) {
            list.fieldsInfo = element.fieldsInfo;
        }
        return list;
    },
    /**
     * Returns the current display_name for the record.
     *
     * @param {string} id the localID for a valid record element
     * @returns {string}
     */
    getName: function (id) {
        var record = this.localData[id];
        if (record._changes && 'display_name' in record._changes) {
            return record._changes.display_name;
        }
        if ('display_name' in record.data) {
            return record.data.display_name;
        }
        return _t("New");
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
            var entry = _.findWhere(parent._savePoint, {operation: 'ADD', id: id});
            if (entry) {
                // 2.1. no drop on non-new addition in list
                if (!entry.isNew) {
                    return false;
                }
                // 2.2. no drop on new addition on "UPDATE"
                var lastEntry = _.last(parent._savePoint);
                if (lastEntry.operation === 'UPDATE' && lastEntry.id === id) {
                    return false;
                }
            }
        }
        // 3. drop new records
        return this.isNew(id);
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
     * @param {any} params
     * @param {Object} [params.fieldsInfo={}] contains the fieldInfo of each field
     * @param {Object} params.fields contains the description of each field
     * @param {string} [params.type] 'record' or 'list'
     * @param {string} [params.recordID] an ID for an existing resource.
     * @returns {Deferred<string>} resolves to a local id, or handle
     */
    load: function (params) {
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
     * This helper method is designed to help developpers that want to use a
     * field widget outside of a view.  In that case, we want a way to create
     * data without actually performing a fetch.
     *
     * @param {string} model name of the model
     * @param {Object[]} fields a description of field properties
     * @param {Object} [fieldInfo] various field info that we want to set
     * @returns {string} the local id for the created resource
     */
    makeRecord: function (model, fields, fieldInfo) {
        var self = this;
        var defs = [];
        var record_fields = {};
        _.each(fields, function (field) {
            record_fields[field.name] = _.pick(field, 'type', 'relation', 'domain');
        });
        fieldInfo = fieldInfo || {};
        var fieldsInfo = {};
        fieldsInfo.default = {};
        _.each(fields, function (field) {
            fieldsInfo.default[field.name] = fieldInfo[field.name] || {};
        });
        var record = this._makeDataPoint({
            modelName: model,
            fields: record_fields,
            fieldsInfo: fieldsInfo,
            viewType: 'default',
        });
        _.each(fields, function (field) {
            var dataPoint;
            record.data[field.name] = null;
            if (field.type === 'many2one') {
                if (field.value) {
                    var id = _.isArray(field.value) ? field.value[0] : field.value;
                    var display_name = _.isArray(field.value) ? field.value[1] : undefined;
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
            } else if (field.type === 'one2many' || field.type === 'many2many') {
                var relatedFieldsInfo = {};
                relatedFieldsInfo.default = {};
                _.each(field.fields, function (field) {
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
                    if (_.isObject(field.value[0])) {
                        dpParams.res_ids = _.pluck(field.value, 'id');
                        dataPoint = self._makeDataPoint(dpParams);
                        _.each(field.value, function (data) {
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
        return $.when.apply($, defs).then(function () {
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
     * @returns {string[]} list of changed fields
     */
    notifyChanges: function (record_id, changes, options) {
        return this.mutex.exec(this._applyChange.bind(this, record_id, changes, options));
    },
    /**
     * Reload all data for a given resource. At any time there is at most one
     * reload operation active.
     *
     * @param {string} id local id for a resource
     * @param {Object} [options]
     * @param {boolean} [options.keepChanges=false] if true, doesn't discard the
     *   changes on the record before reloading it
     * @returns {Deferred<string>} resolves to the id of the resource
     */
    reload: function (id, options) {
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
            parent._changes = _.filter(parent._changes, function (change) {
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
            parent.data = _.without(parent.data, elementID);
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
     * @returns {Deferred<string>} resolves to the local id of the parent
     */
    resequence: function (modelName, resIDs, parentID, options) {
        options = options || {};
        if ((resIDs.length <= 1)) {
            return $.when(parentID); // there is nothing to sort
        }
        var self = this;
        var data = this.localData[parentID];
        var params = {
            model: modelName,
            ids: resIDs,
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
                    return $.when();
                }
                var field = params.field ? params.field : 'sequence';

                return self._rpc({
                    model: modelName,
                    method: 'read',
                    args: [resIDs, [field]],
                }).then(function (records) {
                    if (data.data.length) {
                        var dataType = self.localData[data.data[0]].type;
                        if (dataType === 'record') {
                            _.each(data.data, function (dataPoint) {
                                var recordData = self.localData[dataPoint].data;
                                var inRecords = _.findWhere(records, {id: recordData.id});
                                if (inRecords) {
                                    recordData[field] = inRecords[field];
                                }
                            });
                            data.data = _.sortBy(data.data, function (d) {
                                return self.localData[d].data[field];
                            });
                        }
                        if (dataType === 'list') {
                            data.data = _.sortBy(data.data, function (d) {
                                return _.indexOf(resIDs, self.localData[d].res_id)
                            });
                        }
                    }
                    data.res_ids = [];
                    _.each(data.data, function (d) {
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
     * @returns {Deferred}
     *   Resolved with the list of field names (whose value has been modified)
     */
    save: function (recordID, options) {
        var self = this;
        return this.mutex.exec(function () {
            options = options || {};
            var record = self.localData[recordID];
            if (options.savePoint) {
                self._visitChildren(record, function (rec) {
                    var newValue = rec._changes || rec.data;
                    if (newValue instanceof Array) {
                        rec._savePoint = newValue.slice(0);
                    } else {
                        rec._savePoint = _.extend({}, newValue);
                    }
                });

                // save the viewType of edition, so that the correct readonly modifiers
                // can be evaluated when the record will be saved
                _.each((record._changes || {}), function (value, fieldName) {
                    record._editionViewType[fieldName] = options.viewType;
                });
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
                _.each(fieldNames, function (name) {
                    if (changes[name] === null) {
                        delete changes[name];
                    }
                });
            }

            var def = $.Deferred();
            var changedFields = Object.keys(changes);

            if (options.savePoint) {
                return def.resolve(changedFields);
            }

            def.then(function () {
                record._isDirty = false;
            });
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

                        // Optionally clear the DataManager's cache
                        self._invalidateCache(record);

                        self.unfreezeOrder(record.id);

                        // Update the data directly or reload them
                        if (shouldReload) {
                            self._fetchRecord(record).then(function () {
                                def.resolve(changedFields);
                            });
                        } else {
                            _.extend(record.data, _changes);
                            def.resolve(changedFields);
                        }
                    }).fail(def.reject.bind(def));
            } else {
                def.resolve(changedFields);
            }
            return def;
        });
    },
    /**
     * Completes the fields and fieldsInfo of a dataPoint with the given ones.
     * It is useful for the cases where a record element is shared between
     * various views, such as a one2many with a tree and a form view.
     *
     * @param {string} recordID a valid element ID
     * @param {Object} viewInfo
     * @param {Object} viewInfo.fields
     * @param {Object} viewInfo.fieldsInfo
     */
    addFieldsInfo: function (recordID, viewInfo) {
        var record = this.localData[recordID];
        record.fields = _.extend({}, record.fields, viewInfo.fields);
        // complete the given fieldsInfo with the fields of the main view, so
        // that those field will be reloaded if a reload is triggered by the
        // secondary view
        var fieldsInfo = _.mapObject(viewInfo.fieldsInfo, function (fieldsInfo) {
            return _.defaults({}, fieldsInfo, record.fieldsInfo[record.viewType]);
        });
        record.fieldsInfo = _.extend({}, record.fieldsInfo, fieldsInfo);
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
     * @returns {Deferred}
     */
    setSort: function (list_id, fieldName) {
        var list = this.localData[list_id];
        if (list.type === 'record') {
            return;
        } else if (list._changes) {
            _.each(list._changes, function (change) {
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
            var orderedBy = _.reject(list.orderedBy, function (o) {
                return o.name === fieldName;
            });
            list.orderedBy = [{name: fieldName, asc: true}].concat(orderedBy);
        }

        list.orderedResIDs = null;
        if (list.static) {
            // sorting might require to fetch the field for records where the
            // sort field is still unknown (i.e. on other pages for example)
            return this._fetchUngroupedList(list);
        }
        return $.when();
    },
    /**
     * Toggle the active value of given records (to archive/unarchive them)
     *
     * @param {Array} recordIDs local ids of the records to (un)archive
     * @param {boolean} value false to archive, true to unarchive (value of the active field)
     * @param {string} parentID id of the parent resource to reload
     * @returns {Deferred<string>} resolves to the parent id
     */
    toggleActive: function (recordIDs, value, parentID) {
        var self = this;
        var parent = this.localData[parentID];
        var resIDs = _.map(recordIDs, function (recordID) {
            return self.localData[recordID].res_id;
        });
        return this._rpc({
                model: parent.model,
                method: 'write',
                args: [resIDs, { active: value }],
            })
            .then(function () {
                // optionally clear the DataManager's cache
                self._invalidateCache(parent);
                return self.reload(parentID);
            });
    },
    /**
     * Toggle (open/close) a group in a grouped list, then fetches relevant
     * data
     *
     * @param {string} groupId
     * @returns {Deferred<string>} resolves to the group id
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
            return $.when(groupId);
        }
        if (!group.isOpen) {
            group.isOpen = true;
            var def;
            if (group.count > 0) {
                def = this._load(group).then(function () {
                    self._updateParentResIDs(group);
                });
            }
            return $.when(def).then(function () {
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
            var data = _.extend({}, list.data, list._changes);
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
     * @returns {Deferred<[string]>} resolves to the new records ids
     */
    _addX2ManyDefaultRecord: function (list, options) {
        var self = this;
        var position = options && options.position || 'top';
        var params = {
            fields: list.fields,
            fieldsInfo: list.fieldsInfo,
            parentID: list.id,
            position: position,
            viewType: list.viewType,
            allowWarning: options && options.allowWarning
        };

        var additionalContexts = options && options.context;
        var makeDefaultRecords = [];
        if (additionalContexts){
            _.each(additionalContexts, function (context) {
                params.context = self._getContext(list, {additionalContext: context});
                makeDefaultRecords.push(self._makeDefaultRecord(list.model, params));
            });
        } else {
            params.context = self._getContext(list);
            makeDefaultRecords.push(self._makeDefaultRecord(list.model, params));
        }

        return $.when.apply($, makeDefaultRecords).then(function (){
            var ids = [];
            _.each(arguments, function (id){
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
     * @param {boolean} [options.forceFail=false] if this flag is set to true, then
     *   promise will fail when onchange fails (added as local patch only in stable)
     * @param {boolean} [options.notifyChange=true] if this flag is set to
     *   false, then we will not notify and not trigger the onchange, even though
     *   it was changed.
     * @param {string} [options.viewType] current viewType. If not set, we will assume
     *   main viewType from the record
     * @param {boolean} [options.allowWarning=false] if true, change
     *   operation can complete, even if a warning is raised
     *   (only supported by X2ManyChange)
     * @returns {Deferred} list of changed fields
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
            initialData[elem.id] = $.extend(true, {}, _.pick(elem, 'data', '_changes'));
        });

        // apply changes to local data
        for (var fieldName in changes) {
            field = record.fields[fieldName];
            if (field && (field.type === 'one2many' || field.type === 'many2many')) {
                defs.push(this._applyX2ManyChange(record, fieldName, changes[fieldName], options.viewType, options.allowWarning));
            } else if (field && (field.type === 'many2one' || field.type === 'reference')) {
                defs.push(this._applyX2OneChange(record, fieldName, changes[fieldName]));
            } else {
                record._changes[fieldName] = changes[fieldName];
            }
        }

        if (options.notifyChange === false) {
            return $.Deferred().resolve(_.keys(changes));
        }

        return $.when.apply($, defs).then(function () {
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
            var onchangeDef = $.Deferred();
            if (onChangeFields.length) {
                self._performOnChange(record, onChangeFields, options.viewType)
                    .then(function (result) {
                        delete record._warning;
                        onchangeDef.resolve(_.keys(changes).concat(Object.keys(result && result.value || {})));
                    }).fail(function () {
                        self._visitChildren(record, function (elem) {
                            _.extend(elem, initialData[elem.id]);
                        });
                        // safe fix for stable version, for opw-2267444
                        if (!options.force_fail) {
                            onchangeDef.resolve({});
                        } else {
                            onchangeDef.reject({});
                        }
                    });
            } else {
                onchangeDef = $.Deferred().resolve(_.keys(changes));
            }
            return onchangeDef.then(function (fieldNames) {
                _.each(fieldNames, function (name) {
                    if (record._changes && record._changes[name] === record.data[name]) {
                        delete record._changes[name];
                        record._isDirty = !_.isEmpty(record._changes);
                    }
                });
                return self._fetchSpecialData(record).then(function (fieldNames2) {
                    // Return the names of the fields that changed (onchange or
                    // associated special data change)
                    return _.union(fieldNames, fieldNames2);
                });
            });
        });
    },
    /**
     * Apply an x2one (either a many2one or a reference field) change. There is
     * a need for this function because the server only gives an id when a
     * onchange modifies a many2one field. For this reason, we need (sometimes)
     * to do a /name_get to fetch a display_name.
     *
     * @param {Object} record
     * @param {string} fieldName
     * @param {Object} [data]
     * @returns {Deferred}
     */
    _applyX2OneChange: function (record, fieldName, data) {
        var self = this;
        if (!data || !data.id) {
            record._changes[fieldName] = false;
            return $.when();
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
            return $.when();
        }
        var rel_data = _.pick(data, 'id', 'display_name');
        var field = record.fields[fieldName];

        // the reference field doesn't store its co-model in its field metadata
        // but directly in the data (as the co-model isn't fixed)
        var coModel = field.type === 'reference' ? data.model : field.relation;
        var def;
        if (rel_data.display_name === undefined) {
            // TODO: refactor this to use _fetchNameGet
            def = this._rpc({
                    model: coModel,
                    method: 'name_get',
                    args: [data.id],
                    context: record.context,
                })
                .then(function (result) {
                    rel_data.display_name = result[0][1];
                });
        }
        return $.when(def).then(function () {
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
     * @param {string} [viewType] current viewType. If not set, we will assume
     *   main viewType from the record
     * @returns {Deferred}
     */
    _applyOnChange: function (values, record, viewType) {
        var self = this;
        var defs = [];
        var rec;
        viewType = viewType || record.viewType;
        record._changes = record._changes || {};
        _.each(values, function (val, name) {
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
                return;
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
                    var data = _.isArray(val) ?
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
                } else {
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
                        return; // ignore changes of x2many not in view
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
                _.each(val, function (command) {
                    var rec, recID;
                    if (command[0] === 0 || command[0] === 1) {
                        // CREATE or UPDATE
                        if (command[0] === 0 && command[1]) {
                            // updating an existing (virtual) record
                            var previousChange = _.find(oldChanges, function (operation) {
                                var child = self.localData[operation.id];
                                return child && (child.res_id === command[1]);
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
                        }
                        // Do not abandon the record if it has been created
                        // from `default_get`. The list has a savepoint only
                        // after having fully executed `default_get`.
                        rec._noAbandon = !list._savePoint;
                        list._changes.push({operation: 'ADD', id: rec.id});
                        if (command[0] === 1) {
                            list._changes.push({operation: 'UPDATE', id: rec.id});
                        }
                        defs.push(self._applyOnChange(command[2], rec));
                    } else if (command[0] === 4) {
                        // LINK TO
                        linkRecord(list, command[1]);
                    } else if (command[0] === 5) {
                        // DELETE ALL
                        list._changes = [{operation: 'REMOVE_ALL'}];
                    } else if (command[0] === 6) {
                        list._changes = [{operation: 'REMOVE_ALL'}];
                        _.each(command[2], function (resID) {
                            linkRecord(list, resID);
                        });
                    }
                });
                var def = self._readUngroupedList(list).then(function () {
                    var x2ManysDef = self._fetchX2ManysBatched(list);
                    var referencesDef = self._fetchReferencesBatched(list);
                    return $.when(x2ManysDef, referencesDef);
                });
                defs.push(def);
            } else {
                var newValue = self._parseServerValue(field, val);
                if (newValue !== oldValue) {
                    record._changes[name] = newValue;
                }
            }
        });
        return $.when.apply($, defs);

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
     * @param {string} [viewType] current viewType. If not set, we will assume
     *   main viewType from the record
     * @param {boolean} [allowWarning=false] if true, change
     *   operation can complete, even if a warning is raised
     *   (only supported by the 'CREATE' command.operation)
     * @returns {Deferred}
     */
    _applyX2ManyChange: function (record, fieldName, command, viewType, allowWarning) {
        if (command.operation === 'TRIGGER_ONCHANGE') {
            // the purpose of this operation is to trigger an onchange RPC, so
            // there is no need to apply any change on the record (the changes
            // have probably been already applied and saved, usecase: many2many
            // edition in a dialog)
            return $.when();
        }

        var self = this;
        var localID = (record._changes && record._changes[fieldName]) || record.data[fieldName];
        var list = this.localData[localID];
        var field = record.fields[fieldName];
        var fieldInfo = record.fieldsInfo[viewType || record.viewType][fieldName];
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
                _.defaults(list.fields, newRecord.fields);
                _.defaults(list.fieldsInfo, newRecord.fieldsInfo);
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
                var data = _.isArray(command.ids) ? command.ids : [command.ids];

                // Ensure the local data repository (list) boundaries can handle incoming records (data)
                if (data.length + list.res_ids.length > list.limit) {
                    list.limit = data.length + list.res_ids.length;
                }

                var list_records = {};
                _.each(data, function (d) {
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
                        args: [_.pluck(data, 'id'), fieldNames],
                        context: _.extend({}, record.context, field.context),
                    }).then(function (records) {
                        _.each(records, function (record) {
                            list_records[record.id].data = record;
                            self._parseServerData(fieldNames, list, record);
                        });
                        return $.when(
                            self._fetchX2ManysBatched(list),
                            self._fetchReferencesBatched(list)
                        );
                    });
                    defs.push(def);
                }
                break;
            case 'CREATE':
                var options = {
                    context: command.context,
                    position: command.position,
                    allowWarning: allowWarning
                };
                def = this._addX2ManyDefaultRecord(list, options).then(function (ids) {
                    _.each(ids, function(id){
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
                    defs.push(this._applyChange(command.id, command.data));
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
                list._changes = _.reject(list._changes, function (change, index) {
                    var idInCommands = _.contains(command.ids, change.id);
                    if (idInCommands && change.operation === 'ADD') {
                        idsToRemove = _.without(idsToRemove, change.id);
                    }
                    return idInCommands;
                });
                _.each(idsToRemove, function (id) {
                    var operation = list._forceM2MUnlink ? 'FORGET': 'DELETE';
                    list._changes.push({operation: operation, id: id});
                });
                break;
            case 'REPLACE_WITH':
                // this is certainly not optimal... and not sure that it is
                // correct if some ids are added and some other are removed
                list._changes = [];
                var newIds = _.difference(command.ids, list.res_ids);
                var removedIds = _.difference(list.res_ids, command.ids);
                var addDef, removedDef, values;
                if (newIds.length) {
                    values = _.map(newIds, function (id) {
                        return {id: id};
                    });
                    addDef = this._applyX2ManyChange(record, fieldName, {
                        operation: 'ADD_M2M',
                        ids: values
                    }, viewType);
                }
                if (removedIds.length) {
                    var listData = _.map(list.data, function (localId) {
                        return self.localData[localId];
                    });
                    removedDef = this._applyX2ManyChange(record, fieldName, {
                        operation: 'DELETE',
                        ids: _.map(removedIds, function (resID) {
                            if (resID in list._cache) {
                                return list._cache[resID];
                            }
                            return _.findWhere(listData, {res_id: resID}).id;
                        }),
                    }, viewType);
                }
                return $.when(addDef, removedDef);
        }

        return $.when.apply($, defs).then(function () {
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
        list = _.extend({}, list);
        list.res_ids = list.res_ids.slice(0);
        var changes = list._changes || [];
        if (options) {
            var to = options.to === 0 ? 0 : (options.to || changes.length);
            changes = changes.slice(options.from || 0, to);
        }
        _.each(changes, function (change) {
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
                    list.res_ids = _.without(list.res_ids, relRecord.res_id);
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
     * @see _performOnChange
     *
     * @param {Object} record resource object of type 'record'
     * @param {string} [viewType] current viewType. If not set, we will assume
     *   main viewType from the record
     * @returns {Object|false} an onchange spec, or false if no onchange should
     *   be applied
     */
    _buildOnchangeSpecs: function (record, viewType) {
        var hasOnchange = false;
        var specs = {};
        var fieldsInfo = record.fieldsInfo[viewType || record.viewType];
        generateSpecs(fieldsInfo, record.fields);

        // recursively generates the onchange specs for fields in fieldsInfo,
        // and their subviews
        function generateSpecs (fieldsInfo, fields, prefix) {
            prefix = prefix || '';
            _.each(Object.keys(fieldsInfo), function (name) {
                var field = fields[name];
                var fieldInfo = fieldsInfo[name];
                var key = prefix + name;
                specs[key] = (field.onChange) || "";
                if (field.onChange) {
                    hasOnchange = true;
                }
                _.each(fieldInfo.views, function (view) {
                    generateSpecs(view.fieldsInfo[view.type], view.fields, key + '.');
                });
            });
        }
        return hasOnchange ? specs : false;
    },
    /**
     * Evaluate modifiers
     *
     * @private
     * @param {Object} element a valid element object, which will serve as eval
     *   context.
     * @param {Object} modifiers
     * @returns {Object}
     */
    _evalModifiers: function (element, modifiers) {
        var result = {};
        var self = this;
        var evalContext;
        function evalModifier(mod) {
            if (mod === undefined || mod === false || mod === true) {
                return !!mod;
            }
            evalContext = evalContext || self._getEvalContext(element);
            return new Domain(mod, evalContext).compute(evalContext);
        }
        if ('invisible' in modifiers) {
            result.invisible = evalModifier(modifiers.invisible);
        }
        if ('column_invisible' in modifiers) {
            result.column_invisible = evalModifier(modifiers.column_invisible);
        }
        if ('readonly' in modifiers) {
            result.readonly = evalModifier(modifiers.readonly);
        }
        if ('required' in modifiers) {
            result.required = evalModifier(modifiers.required);
        }
        return result;
    },
    /**
     * Fetch all name_gets for the many2ones in a group
     *
     * @param {Object[]} groups a list of object with context and record sub keys
     * @returns {Deferred}
     */
    _fetchMany2OneGroup: function (groups) {
        var ids = _.uniq(_.pluck(_.pluck(groups, 'record'), 'res_id'));
        return this._rpc({
                model: groups[0].record.model,
                method: 'name_get',
                args: [ids],
                context: groups[0].context
            })
            .then(function (name_gets) {
                _.each(groups, function (obj) {
                    var nameGet = _.find(name_gets, function (n) { return n[0] === obj.record.res_id;});
                    obj.record.data.display_name = nameGet[1];
                });
            });
    },
    /**
     * Fetch name_get for a record datapoint.
     *
     * @param {Object} dataPoint
     * @returns {Deferred}
     */
    _fetchNameGet: function (dataPoint) {
        return this._rpc({
            model: dataPoint.model,
            method: 'name_get',
            args: [dataPoint.res_id],
            context: dataPoint.getContext(),
        }).then(function (result) {
            dataPoint.data.display_name = result[0][1];
        });
    },
    /**
     * Fetch name_get for a field of type Many2one or Reference
     *
     * @private
     * @params {Object} list: must be a datapoint of type list
     *   (for example: a datapoint representing a x2many)
     * @params {string} fieldName: the name of a field of type Many2one or Reference
     * @returns {Deferred}
     */
    _fetchNameGets: function (list, fieldName) {
        var self = this;
        // We first get the model this way because if list.data is empty
        // the _.each below will not make it.
        var model = list.fields[fieldName].relation;
        var records = [];
        var ids = [];
        list = this._applyX2ManyOperations(list);

        _.each(list.data, function (localId) {
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
            return $.when();
        }
        return this._rpc({
                model: model,
                method: 'name_get',
                args: [_.uniq(ids)],
                context: list.context,
            })
            .then(function (name_gets) {
                _.each(records, function (record) {
                    var nameGet = _.find(name_gets, function (nameGet) {
                        return nameGet[0] === record.data.id;
                    });
                    record.data.display_name = nameGet[1];
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
     * @returns {Deferred<Object>} resolves to the record or is rejected in
     *   case no id given were valid ids
     */
    _fetchRecord: function (record, options) {
        var self = this;
        options = options || {};
        var fieldNames = options.fieldNames || record.getFieldNames(options);
        fieldNames = _.uniq(fieldNames.concat(['display_name']));
        return this._rpc({
                model: record.model,
                method: 'read',
                args: [[record.res_id], fieldNames],
                context: _.extend({}, record.getContext(), {bin_size: true}),
            })
            .then(function (result) {
                if (result.length === 0) {
                    return $.Deferred().reject();
                }
                result = result[0];
                record.data = _.extend({}, record.data, result);
            })
            .then(function () {
                self._parseServerData(fieldNames, record, record.data);
            })
            .then(function () {
                return $.when(
                    self._fetchX2Manys(record, options),
                    self._fetchReferences(record, options)
                ).then(function () {
                    return self._postprocess(record, options);
                });
            });
    },
    /**
     * Fetch the `name_get` for a reference field.
     *
     * @private
     * @param {Object} record
     * @param {string} fieldName
     * @returns {Deferred}
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
                method: 'name_get',
                args: [resID],
                context: record.getContext({fieldName: fieldName}),
            }).then(function (result) {
                return self._makeDataPoint({
                    data: {
                        id: result[0][0],
                        display_name: result[0][1],
                    },
                    modelName: model,
                    parentID: record.id,
                });
            });
        }
        return $.when(def);
    },
    /**
     * Fetch the extra data (`name_get`) for the reference fields of the record
     * model.
     *
     * @private
     * @param {Object} record
     * @returns {Deferred}
     */
    _fetchReferences: function (record, options) {
        var self = this;
        var defs = [];
        var fieldNames = options && options.fieldNames || record.getFieldNames();
        _.each(fieldNames, function (fieldName) {
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
        return $.when.apply($, defs);
    },
    /**
     * Batch requests for one reference field in list (one request by different
     * model in the field values).
     *
     * @see _fetchReferencesBatched
     * @param {Object} list
     * @param {string} fieldName
     * @returns {Deferred}
     */
    _fetchReferenceBatched: function (list, fieldName) {
        var self = this;
        list = this._applyX2ManyOperations(list);

        // collect ids by model
        var toFetch = {};
        _.each(list.data, function (dataPoint) {
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

        var defs = [];
        var def;
        // one name_get by model
        _.each(toFetch, function (datapoints, model) {
            var ids = _.map(Object.keys(datapoints), function (id) { return parseInt(id); });
            // we need one parent for the context (they all have the same)
            var parent = datapoints[ids[0]][0];
            def = self._rpc({
                model: model,
                method: 'name_get',
                args: [ids],
                context: self.localData[parent].getContext({fieldName: fieldName}),
            }).then(function (result) {
                _.each(result, function (el) {
                    var parentIDs = datapoints[el[0]];
                    _.each(parentIDs, function (parentID) {
                        var parent = self.localData[parentID];
                        var referenceDp = self._makeDataPoint({
                            data: {
                                id: el[0],
                                display_name: el[1],
                            },
                            modelName: model,
                            parentID: parent,
                        });
                        parent.data[fieldName] = referenceDp.id;
                    });
                });
            });
            defs.push(def);
        });

        return $.when.apply($, defs);
    },
    /**
     * Batch requests for references for datapoint of type list.
     *
     * @param {Object} list
     * @returns {Deferred}
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
        return $.when.apply($, defs);
    },
    /**
     * This method is incorrectly named.  It should be named something like
     * _fetchMany2OneData.
     *
     * For a given record, this method fetches all many2ones information,
     * batching the requests if possible (for example, if 3 many2ones are in
     * relation on the same model, then we can probably fetch them in one rpc)
     *
     * This method is currently only called by _makeDefaultRecord, it should be
     * called by the onchange methods at some point.
     *
     * @todo fix bug: returns a list of deferred, not a deferred
     *
     * @param {Object} record a valid resource object
     * @returns {Deferred}
     */
    _fetchRelationalData: function (record) {
        var self = this;
        var toBeFetched = [];

        // find all many2one related records to be fetched
        _.each(record.getFieldNames(), function (name) {
            var field = record.fields[name];
            if (field.type === 'many2one' && !record.fieldsInfo[record.viewType][name].__no_fetch) {
                var localId = (record._changes && record._changes[name]) || record.data[name];
                var relatedRecord = self.localData[localId];
                if (!relatedRecord || relatedRecord.data.display_name) {
                    return;
                }
                toBeFetched.push({
                    context: record.getContext({fieldName: name, viewType: record.viewType}),
                    record: relatedRecord
                });
            }
        });

        // group them by model and context. Using the context as key is
        // necessary to make sure the correct context is used for the rpc;
        var groups = _.groupBy(toBeFetched, function (elem) {
            return [elem.record.model, JSON.stringify(elem.context)].join();
        });

        return $.when.apply($, _.map(groups, this._fetchMany2OneGroup.bind(this)));
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
     * @returns {Deferred<Array>}
     *          The deferred is resolved with an array containing the names of
     *          the field whose special data has been changed.
     */
    _fetchSpecialData: function (record, options) {
        var self = this;
        var specialFieldNames = [];
        var fieldNames = (options && options.fieldNames) || record.getFieldNames();
        return $.when.apply($, _.map(fieldNames, function (name) {
            var viewType = (options && options.viewType) || record.viewType;
            var fieldInfo = record.fieldsInfo[viewType][name] || {};
            var Widget = fieldInfo.Widget;
            if (Widget && Widget.prototype.specialData) {
                return self[Widget.prototype.specialData](record, name, fieldInfo).then(function (data) {
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
     * @returns {Deferred<any>}
     *          The deferred is resolved with the fetched special data. If this
     *          data is the same as the previously fetched one (for the given
     *          parameters), no RPC is done and the deferred is resolved with
     *          the undefined value.
     */
    _fetchSpecialMany2ones: function (record, fieldName, fieldInfo, fieldsToRead) {
        var field = record.fields[fieldName];
        if (field.type !== "many2one") {
            return $.when();
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
            return $.when();
        }

        var self = this;
        return this._rpc({
                model: field.relation,
                method: 'search_read',
                fields: ["id"].concat(fieldsToRead || []),
                context: context,
                domain: domain,
            })
            .then(function (records) {
                var ids = _.pluck(records, 'id');
                return self._rpc({
                        model: field.relation,
                        method: 'name_get',
                        args: [ids],
                        context: context,
                    })
                    .then(function (name_gets) {
                        _.each(records, function (rec) {
                            var name_get = _.find(name_gets, function (n) {
                                return n[0] === rec.id;
                            });
                            rec.display_name = name_get[1];
                        });
                        return records;
                    });
            });
    },
    /**
     * Fetches all the relation records associated to the given fieldName. If
     * the given fieldName is not a relational field, nothing is done.
     *
     * @param {Object} record - an element from the localData
     * @param {Object} fieldName - the name of the field
     * @returns {Deferred<any>}
     *          The deferred is resolved with the fetched special data. If this
     *          data is the same as the previously fetched one (for the given
     *          parameters), no RPC is done and the deferred is resolved with
     *          the undefined value.
     */
    _fetchSpecialRelation: function (record, fieldName) {
        var field = record.fields[fieldName];
        if (!_.contains(["many2one", "many2many", "one2many"], field.type)) {
            return $.when();
        }

        var context = record.getContext({fieldName: fieldName});
        var domain = record.getDomain({fieldName: fieldName});

        // avoid rpc if not necessary
        var hasChanged = this._saveSpecialDataCache(record, fieldName, {
            context: context,
            domain: domain,
        });
        if (!hasChanged) {
            return $.when();
        }

        return this._rpc({
                model: field.relation,
                method: 'name_search',
                args: ["", domain],
                context: context
            });
    },
    /**
     * Fetches the `name_get` associated to the reference widget if the field is
     * a `char` (which is a supported case).
     *
     * @private
     * @param {Object} record - an element from the localData
     * @param {Object} fieldName - the name of the field
     * @returns {Deferred}
     */
    _fetchSpecialReference: function (record, fieldName) {
        var def;
        var field = record.fields[fieldName];
        if (field.type === 'char') {
            // if the widget reference is set on a char field, the name_get
            // needs to be fetched a posteriori
            def = this._fetchReference(record, fieldName);
        }
        return $.when(def);
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
     * @returns {Deferred<any>}
     *          The deferred is resolved with the fetched special data. If this
     *          data is the same as the previously fetched one (for the given
     *          parameters), no RPC is done and the deferred is resolved with
     *          the undefined value.
     */
    _fetchSpecialStatus: function (record, fieldName, fieldInfo) {
        var foldField = fieldInfo.options.fold_field;
        var fieldsToRead = foldField ? [foldField] : [];
        return this._fetchSpecialMany2ones(record, fieldName, fieldInfo, fieldsToRead).then(function (m2os) {
            _.each(m2os, function (m2o) {
                m2o.fold = foldField ? m2o[foldField] : false;
            });
            return m2os;
        });
    },
    /**
     * Fetches the number of records associated to the domain the value of the
     * given field represents.
     *
     * @param {Object} record - an element from the localData
     * @param {Object} fieldName - the name of the field
     * @param {Object} fieldInfo
     * @returns {Deferred<any>}
     *          The deferred is resolved with the fetched special data. If this
     *          data is the same as the previously fetched one (for the given
     *          parameters), no RPC is done and the deferred is resolved with
     *          the undefined value.
     */
    _fetchSpecialDomain: function (record, fieldName, fieldInfo) {
        var context = record.getContext({fieldName: fieldName});

        var domainModel = fieldInfo.options.model;
        if (record.data.hasOwnProperty(domainModel)) {
            domainModel = record._changes && record._changes[domainModel] || record.data[domainModel];
        }
        var domainValue = record._changes && record._changes[fieldName] || record.data[fieldName] || [];

        // avoid rpc if not necessary
        var hasChanged = this._saveSpecialDataCache(record, fieldName, {
            context: context,
            domainModel: domainModel,
            domainValue: domainValue,
        });
        if (!hasChanged) {
            return $.when();
        } else if (!domainModel) {
            return $.when({
                model: domainModel,
                nbRecords: 0,
            });
        }

        var def = $.Deferred();
        var evalContext = this._getEvalContext(record);
        this._rpc({
                model: domainModel,
                method: 'search_count',
                args: [Domain.prototype.stringToArray(domainValue, evalContext)],
                context: context
            })
            .then(_.identity, function (error, e) {
                e.preventDefault(); // prevent traceback (the search_count might be intended to break)
                return false;
            })
            .always(function (nbRecords) {
                def.resolve({
                    model: domainModel,
                    nbRecords: nbRecords,
                });
            });

        return def;
    },
    /**
     * Fetch all data in a ungrouped list
     *
     * @param {Object} list a valid resource object
     * @returns {Deferred<Object>} resolves to the fecthed list
     */
    _fetchUngroupedList: function (list) {
        var self = this;
        var def;
        if (list.static) {
            def = this._readUngroupedList(list).then(function () {
                if (list.parentID && self.isNew(list.parentID)) {
                    // list from a default_get, so fetch display_name for many2one fields
                    var many2ones = self._getMany2OneFieldNames(list);
                    var defs = _.map(many2ones, function (name) {
                        return self._fetchNameGets(list, name);
                    });
                    return $.when.apply($, defs);
                }
            });
        } else {
            def = this._searchReadUngroupedList(list);
        }
        return def.then(function () {
            return $.when(
                self._fetchX2ManysBatched(list),
                self._fetchReferencesBatched(list));
        }).then(function () {
            return list;
        });
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
     * @returns {Deferred}
     */
    _fetchX2Manys: function (record, options) {
        var self = this;
        var defs = [];
        options = options || {};
        var fieldNames = options.fieldNames || record.getFieldNames(options);
        var viewType = options.viewType || record.viewType;
        _.each(fieldNames, function (fieldName) {
            var field = record.fields[fieldName];
            if (field.type === 'one2many' || field.type === 'many2many') {
                var fieldInfo = record.fieldsInfo[viewType][fieldName];
                var rawContext = fieldInfo && fieldInfo.context;
                var view = fieldInfo.views && fieldInfo.views[fieldInfo.mode];
                var fieldsInfo = view ? view.fieldsInfo : (fieldInfo.fieldsInfo || {});
                var ids = record.data[fieldName] || [];
                var list = self._makeDataPoint({
                    count: ids.length,
                    context: _.extend({}, record.context, field.context),
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
                    var def = self._readUngroupedList(list).then(function () {
                        return $.when(
                            self._fetchX2ManysBatched(list),
                            self._fetchReferencesBatched(list)
                        );
                    });
                    defs.push(def);
                }
            }
        });
        return $.when.apply($, defs);
    },
    /**
     * batch requests for 1 x2m in list
     *
     * @see _fetchX2ManysBatched
     * @param {Object} list
     * @param {string} fieldName
     * @returns {Deferred}
     */
    _fetchX2ManyBatched: function (list, fieldName) {
        var self = this;
        var field = list.fields[fieldName];
        var fieldInfo = list.fieldsInfo[list.viewType][fieldName];
        var view = fieldInfo.views && fieldInfo.views[fieldInfo.mode];
        var fieldsInfo = view ? view.fieldsInfo : fieldInfo.fieldsInfo;
        var fields = view ? view.fields : fieldInfo.relatedFields;
        var viewType = view ? view.type : fieldInfo.viewType;
        list = this._applyX2ManyOperations(list);
        this._sortList(list);
        var x2mRecords = [];

        // step 1: collect ids
        var ids = [];
        _.each(list.data, function (dataPoint) {
            var record = self.localData[dataPoint];
            if (typeof record.data[fieldName] === 'string') {
                // in this case, the value is a local ID, which means that the
                // record has already been processed. It can happen for example
                // when a user adds a record in a m2m relation, or loads more
                // records in a kanban column
                return;
            }
            x2mRecords.push(record);
            ids = _.unique(ids.concat(record.data[fieldName] || []));
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

        if (!ids.length || fieldInfo.__no_fetch) {
            return $.when();
        }
        var def;
        var fieldNames = _.keys(fieldInfo.relatedFields);
        // step 2: fetch data from server
        // if we want specific fields
        // if not we return an array of objects with the id
        // to avoid fetching all the relation fields and an useless rpc
        if (fieldNames.length) {
            def = this._rpc({
                model: field.relation,
                method: 'read',
                args: [ids, fieldNames],
                context: list.getContext() || {},
            });
        } else {
            def = $.when(_.map(ids, function (id) {
                return {id:id};
            }));
        }
        return def.then(function (results) {
            // step 3: assign values to correct datapoints
            _.each(x2mRecords, function (record) {
                var m2mList = self.localData[record.data[fieldName]];
                m2mList.data = [];
                _.each(m2mList.res_ids, function (res_id) {
                    var dataPoint = self._makeDataPoint({
                        modelName: field.relation,
                        data: _.findWhere(results, {id: res_id}),
                        fields: fields,
                        fieldsInfo: fieldsInfo,
                        parentID: m2mList.id,
                        viewType: viewType,
                    });
                    m2mList.data.push(dataPoint.id);
                    m2mList._cache[res_id] = dataPoint.id;
                });
            });
        });
    },
    /**
     * batch request for x2ms for datapoint of type list
     *
     * @param {Object} list
     * @returns {Deferred}
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
        return $.when.apply($, defs);
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
        if ('changesOnly' in options && !options.changesOnly) {
            changes = _.extend({}, record.data, record._changes);
        } else {
            changes = _.extend({}, record._changes);
        }
        var withReadonly = options.withReadonly || false;
        var commands = this._generateX2ManyCommands(record, {
            changesOnly: 'changesOnly' in options ? options.changesOnly : true,
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
                if (commands[fieldName] && commands[fieldName].length) { // replace localId by commands
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
        options = _.extend({}, options || {}, {withReadonly: true});
        var commands = this._generateX2ManyCommands(record, options);
        var data = _.extend(this.get(record.id, {raw: true}).data, commands);
        // 'display_name' is automatically added to the list of fields to fetch,
        // when fetching a record, even if it doesn't appear in the view. However,
        // only the fields in the view must be passed to the onchange RPC, so we
        // remove it from the data sent by RPC if it isn't in the view.
        var hasDisplayName = _.some(record.fieldsInfo, function (fieldsInfo) {
            return 'display_name' in fieldsInfo;
        });
        if (!hasDisplayName) {
            delete data.display_name;
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
        var fields = record.fields;
        if (options.fieldNames) {
            fields = _.pick(fields, options.fieldNames);
        }
        var commands = {};
        var data = _.extend({}, record.data, record._changes);
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
                _.each(list._changes, function (change) {
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
                    var relRecordCreated = _.filter(relRecordAdded, function (rec) {
                        return typeof rec.res_id === 'string';
                    });
                    var realIDs = _.difference(list.res_ids, _.pluck(relRecordCreated, 'res_id'));
                    // deliberately generate a single 'replace' command instead
                    // of a 'delete' and a 'link' commands with the exact diff
                    // because 1) performance-wise it doesn't change anything
                    // and 2) to guard against concurrent updates (policy: force
                    // a complete override of the actual value of the m2m)
                    commands[fieldName].push(x2ManyCommands.replace_with(realIDs));
                    _.each(relRecordCreated, function (relRecord) {
                        var changes = self._generateChanges(relRecord, options);
                        commands[fieldName].push(x2ManyCommands.create(relRecord.ref, changes));
                    });
                    // generate update commands for records that have been
                    // updated (it may happen with editable lists)
                    _.each(relRecordUpdated, function (relRecord) {
                        var changes = self._generateChanges(relRecord, options);
                        if (!_.isEmpty(changes)) {
                            var command = x2ManyCommands.update(relRecord.res_id, changes);
                            commands[fieldName].push(command);
                        }
                    });
                } else if (type === 'one2many') {
                    var removedIds = _.difference(oldResIDs, list.res_ids);
                    var addedIds = _.difference(list.res_ids, oldResIDs);
                    var keptIds = _.intersection(oldResIDs, list.res_ids);

                    // the didChange variable keeps track of the fact that at
                    // least one id was updated
                    var didChange = false;
                    var changes, command, relRecord;
                    for (var i = 0; i < list.res_ids.length; i++) {
                        if (_.contains(keptIds, list.res_ids[i])) {
                            // this is an id that already existed
                            relRecord = _.findWhere(relRecordUpdated, {res_id: list.res_ids[i]});
                            changes = relRecord ? this._generateChanges(relRecord, options) : {};
                            if (!_.isEmpty(changes)) {
                                command = x2ManyCommands.update(relRecord.res_id, changes);
                                didChange = true;
                            } else {
                                command = x2ManyCommands.link_to(list.res_ids[i]);
                            }
                            commands[fieldName].push(command);
                        } else if (_.contains(addedIds, list.res_ids[i])) {
                            // this is a new id (maybe existing in DB, but new in JS)
                            relRecord = _.findWhere(relRecordAdded, {res_id: list.res_ids[i]});
                            if (!relRecord) {
                                commands[fieldName].push(x2ManyCommands.link_to(list.res_ids[i]));
                                continue;
                            }
                            changes = this._generateChanges(relRecord, options);
                            if (!this.isNew(relRecord.id)) {
                                // the subrecord already exists in db
                                commands[fieldName].push(x2ManyCommands.link_to(relRecord.res_id));
                                delete changes.id;
                                if (!_.isEmpty(changes)) {
                                    commands[fieldName].push(x2ManyCommands.update(relRecord.res_id, changes));
                                }
                            } else {
                                // the subrecord is new, so create it
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
     * @returns {Object} the evaluated context
     */
    _getContext: function (element, options) {
        options = options || {};
        var context = new Context(session.user_context);
        context.set_eval_context(this._getEvalContext(element));

        if (options.full || !(options.fieldName || options.additionalContext)) {
            context.add(element.context);
        }
        if (options.fieldName) {
            var viewType = options.viewType || element.viewType;
            var fieldInfo = element.fieldsInfo[viewType][options.fieldName];
            if (fieldInfo && fieldInfo.context) {
                context.add(fieldInfo.context);
            } else {
                var fieldParams = element.fields[options.fieldName];
                if (fieldParams.context) {
                    context.add(fieldParams.context);
                }
            }
        }
        if (options.additionalContext) {
            context.add(options.additionalContext);
        }
        if (element.rawContext) {
            var rawContext = new Context(element.rawContext);
            var evalContext = this._getEvalContext(this.localData[element.parentID]);
            evalContext.id = evalContext.id || false;
            rawContext.set_eval_context(evalContext);
            context.add(rawContext);
        }

        return context.eval();
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
     * @returns {Object}
     */
    _getEvalContext: function (element, forDomain) {
        var evalContext = element.type === 'record' ? this._getRecordEvalContext(element, forDomain) : {};

        if (element.parentID) {
            var parent = this.localData[element.parentID];
            if (parent.type === 'list' && parent.parentID) {
                parent = this.localData[parent.parentID];
            }
            if (parent.type === 'record') {
                evalContext.parent = this._getRecordEvalContext(parent, forDomain);
            }
        }
        return _.extend({
            active_id: evalContext.id || false,
            active_ids: evalContext.id ? [evalContext.id] : [],
            active_model: element.model,
            current_date: moment().format('YYYY-MM-DD'),
            id: evalContext.id || false,
        }, session.user_context, element.context, evalContext);
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
     * Get many2one fields names in a datapoint. This is useful in order to
     * fetch their names in the case of a default_get.
     *
     * @private
     * @param {Object} datapoint a valid resource object
     * @returns {string[]} list of field names that are many2one
     */
    _getMany2OneFieldNames: function (datapoint) {
        var many2ones = [];
        _.each(datapoint.fields, function (field, name) {
            if (field.type === 'many2one') {
                many2ones.push(name);
            }
        });
        return many2ones;
    },
    /**
     * Evaluate the record evaluation context.  This method is supposed to be
     * called by _getEvalContext.  It basically only generates a dictionary of
     * current values for the record, with commands for x2manys fields.
     *
     * @param {Object} record an element of type 'record'
     * @param {boolean} [forDomain=false] if true, x2many values are a list of
     *   ids instead of a list of commands
     * @returns Object
     */
    _getRecordEvalContext: function (record, forDomain) {
        var self = this;
        var relDataPoint;
        var context = _.extend({}, record.data, record._changes);

        // calls _generateX2ManyCommands for a given field, and returns the array of commands
        function _generateX2ManyCommands(fieldName) {
            var commands = self._generateX2ManyCommands(record, {fieldNames: [fieldName]});
            return commands[fieldName];
        }

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
                if (!context[fieldName] || _.isArray(context[fieldName])) { // no dataPoint created yet
                    ids = context[fieldName] ? context[fieldName].slice(0) : [];
                } else {
                    relDataPoint = this._applyX2ManyOperations(this.localData[context[fieldName]]);
                    ids = relDataPoint.res_ids.slice(0);
                }
                if (!forDomain) {
                    // when sent to the server, the x2manys values must be a list
                    // of commands in a context, but the list of ids in a domain
                    ids.toJSON = _generateX2ManyCommands.bind(null, fieldName);
                } else if (field.type === 'one2many') { // Ids are evaluated as a list of ids
                    /* Filtering out virtual ids from the ids list
                     * The server will crash if there are virtual ids in there
                     * The webClient doesn't do literal id list comparison like ids == list
                     * Only relevant in o2m: m2m does create actual records in db
                     */
                    ids = _.filter(ids, function (id) {
                        return typeof id !== 'string';
                    });
                }
                context[fieldName] = ids;
            }

        }
        return context;
    },
    /**
     * Invalidates the DataManager's cache if the main model (i.e. the model of
     * its root parent) of the given dataPoint is a model in 'noCacheModels'.
     *
     * @private
     * @param {Object} dataPoint
     */
    _invalidateCache: function (dataPoint) {
        while (dataPoint.parentID) {
            dataPoint = this.localData[dataPoint.parentID];
        }
        if (_.contains(this.noCacheModels, dataPoint.model)) {
            core.bus.trigger('clear_cache');
        }
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
        var fieldInfo = record.fieldsInfo &&
                        (record.fieldsInfo[viewType || record.viewType][fieldName]);
        if (fieldInfo) {
            var rawModifiers = fieldInfo.modifiers || {};
            var modifiers = this._evalModifiers(record, rawModifiers);
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
        _.each(element._changes, function (command) {
            if (command.operation === 'DELETE' ||
                    command.operation === 'FORGET' ||
                    (command.operation === 'ADD' &&  !command.isNew)||
                    command.operation === 'REMOVE_ALL') {
                return;
            }
            var recordData = self.get(command.id, {raw: true}).data;
            var record = self.localData[command.id];
            _.each(element.getFieldNames(), function (fieldName) {
                var field = element.fields[fieldName];
                var fieldInfo = element.fieldsInfo[element.viewType][fieldName];
                var rawModifiers = fieldInfo.modifiers || {};
                var modifiers = self._evalModifiers(record, rawModifiers);
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
     * @returns {Deferred}
     */
    _load: function (dataPoint, options) {
        if (options && options.onlyGroups &&
          !(dataPoint.type === 'list' && dataPoint.groupedBy.length)) {
            return $.when(dataPoint);
        }

        if (dataPoint.type === 'record') {
            return this._fetchRecord(dataPoint, options);
        }
        if (dataPoint.type === 'list' && dataPoint.groupedBy.length) {
            return this._readGroup(dataPoint, options);
        }
        if (dataPoint.type === 'list' && !dataPoint.groupedBy.length) {
            return this._fetchUngroupedList(dataPoint);
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
     * @param {string} [params.viewType] the type of the view, e.g. 'list' or 'form'
     * @returns {Object} the resource created
     */
    _makeDataPoint: function (params) {
        var type = params.type || ('domain' in params && 'list') || 'record';
        var res_id, value;
        var res_ids = params.res_ids || [];
        var data = params.data || (type === 'record' ? {} : []);
        var context = params.context;
        if (type === 'record') {
            res_id = params.res_id || (params.data && params.data.id);
            if (res_id) {
                data.id = res_id;
            } else {
                res_id = _.uniqueId('virtual_');
            }
            // it doesn't make sense for a record datapoint to have those keys
            // besides, it will mess up x2m and actions down the line
            context = _.omit(context, ['orderedBy', 'group_by']);
        } else {
            var isValueArray = params.value instanceof Array;
            res_id = isValueArray ? params.value[0] : undefined;
            value = isValueArray ? params.value[1] : params.value;
        }

        var fields = _.extend({
            display_name: {type: 'char'},
            id: {type: 'integer'},
        }, params.fields);

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
            groupedBy: params.groupedBy || [],
            id: _.uniqueId(params.modelName + '_'),
            isOpen: params.isOpen,
            limit: type === 'record' ? 1 : params.limit,
            loadMoreOffset: 0,
            model: params.modelName,
            offset: params.offset || (type === 'record' ? _.indexOf(res_ids, res_id) : 0),
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
     * @returns {Deferred<string>} resolves to the id for the created resource
     */
    _makeDefaultRecord: function (modelName, params) {
        var self = this;

        var targetView = params.viewType;
        var fields = params.fields;
        var fieldsInfo = params.fieldsInfo;
        var fieldNames = Object.keys(fieldsInfo[targetView]);
        var fields_key = _.without(fieldNames, '__last_update');

        // Fields that are present in the originating view, that need to be initialized
        // Hence preventing their value to crash when getting back to the originating view
        var parentRecord = self.localData[params.parentID];
        if (parentRecord) {
            var originView = parentRecord.viewType;
            fieldNames = _.union(fieldNames, Object.keys(parentRecord.fieldsInfo[originView]));
            fieldsInfo[targetView] = _.defaults({}, fieldsInfo[targetView], parentRecord.fieldsInfo[originView]);
            fields = _.defaults({}, fields, parentRecord.fields);
        }

        return this._rpc({
                model: modelName,
                method: 'default_get',
                args: [fields_key],
                context: params.context,
            })
            .then(function (result) {
                var record = self._makeDataPoint({
                    modelName: modelName,
                    fields: fields,
                    fieldsInfo: fieldsInfo,
                    context: params.context,
                    parentID: params.parentID,
                    res_ids: params.res_ids,
                    viewType: targetView,
                });

                // We want to overwrite the default value of the handle field (if any),
                // in order for new lines to be added at the correct position.
                // -> This is a rare case where the defaul_get from the server
                //    will be ignored by the view for a certain field (usually "sequence").

                var overrideDefaultFields = self._computeOverrideDefaultFields(
                    params.parentID,
                    params.position
                );

                if (overrideDefaultFields) {
                    result[overrideDefaultFields.field] = overrideDefaultFields.value;
                }

                return self.applyDefaultValues(record.id, result, {fieldNames: fieldNames})
                    .then(function () {
                        var def = $.Deferred();
                        self._performOnChange(record, fields_key).always(function () {
                            if (record._warning) {
                                if (params.allowWarning) {
                                    delete record._warning;
                                } else {
                                    def.reject();
                                }
                            }
                            def.resolve();
                        });
                        return def;
                    })
                    .then(function () {
                        return self._fetchRelationalData(record);
                    })
                    .then(function () {
                        return self._postprocess(record);
                    })
                    .then(function () {
                        // save initial changes, so they can be restored later,
                        // if we need to discard.
                        self.save(record.id, {savePoint: true});

                        return record.id;
                    });
            });
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
        _.each(fieldNames, function (fieldName) {
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
     * @param {string[]} fields changed fields
     * @param {string} [viewType] current viewType. If not set, we will assume
     *   main viewType from the record
     * @returns {Deferred}
     */
    _performOnChange: function (record, fields, viewType) {
        var self = this;
        var onchangeSpec = this._buildOnchangeSpecs(record, viewType);
        if (!onchangeSpec) {
            return $.when();
        }
        var idList = record.data.id ? [record.data.id] : [];
        var options = {
            full: true,
        };
        if (fields.length === 1) {
            fields = fields[0];
            // if only one field changed, add its context to the RPC context
            options.fieldName = fields;
        }
        var context = this._getContext(record, options);
        var currentData = this._generateOnChangeData(record, {changesOnly: false});

        return self._rpc({
                model: record.model,
                method: 'onchange',
                args: [idList, currentData, fields, onchangeSpec, context],
            })
            .then(function (result) {
                if (!record._changes) {
                    // if the _changes key does not exist anymore, it means that
                    // it was removed by discarding the changes after the rpc
                    // to onchange. So, in that case, the proper response is to
                    // ignore the onchange.
                    return;
                }
                if (result.warning) {
                    self.trigger_up('warning', {
                        message: result.warning.message,
                        title: result.warning.title,
                        type: 'dialog',
                    });
                    record._warning = true;
                }
                if (result.domain) {
                    record._domains = _.extend(record._domains, result.domain);
                }
                return self._applyOnChange(result.value, record).then(function () {
                    return result;
                });
            });
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
     * @returns {Deferred<Object>} resolves to the finished resource
     */
    _postprocess: function (record, options) {
        var self = this;
        var viewType = options && options.viewType || record.viewType;
        var defs = [];

        _.each(record.getFieldNames(options), function (name) {
            var field = record.fields[name];
            var fieldInfo = record.fieldsInfo[viewType][name] || {};
            var options = fieldInfo.options || {};
            if (options.always_reload) {
                if (record.fields[name].type === 'many2one' && record.data[name]) {
                    var element = self.localData[record.data[name]];
                    defs.push(self._rpc({
                            model: field.relation,
                            method: 'name_get',
                            args: [element.data.id],
                            context: self._getContext(record, {fieldName: name, viewType: viewType}),
                        })
                        .then(function (result) {
                            element.data.display_name = result[0][1];
                        }));
                }
            }
        });

        defs.push(this._fetchSpecialData(record, options));

        return $.when.apply($, defs).then(function () {
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
     * @returns {Deferred}
     */
    _processX2ManyCommands: function (record, fieldName, commands, options) {
        var self = this;
        options = options || {};
        var defs = [];
        var field = record.fields[fieldName];
        var fieldInfo = record.fieldsInfo[options.viewType || record.viewType][fieldName];
        var view = fieldInfo.views && fieldInfo.views[fieldInfo.mode];
        var fieldsInfo = view ? view.fieldsInfo : fieldInfo.fieldsInfo;
        var fields = view ? view.fields : fieldInfo.relatedFields;
        var viewType = view ? view.type : fieldInfo.viewType;

        // remove default_* keys from parent context to avoid issue of same field name in x2m
        var parentContext = _.omit(record.context, function (val, key) {
            return _.str.startsWith(key, 'default_');
        });
        var x2manyList = self._makeDataPoint({
            context: parentContext,
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
        var isCommandList = commands.length && _.isArray(commands[0]);
        if (!isCommandList) {
            commands = [[6, false, commands]];
        }
        _.each(commands, function (value) {
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
                _.each(r.getFieldNames(), function (fieldName) {
                    r.data[fieldName] = null;
                });

                r._changes = _.defaults(value[2], r.data);
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
                        } else if (_.contains(['one2many', 'many2many'], fieldType)) {
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
                _.each(value[2], function (res_id) {
                    x2manyList._changes.push({operation: 'ADD', resID: res_id});
                });
                var def = self._readUngroupedList(x2manyList).then(function () {
                    return $.when(
                        self._fetchX2ManysBatched(x2manyList),
                        self._fetchReferencesBatched(x2manyList)
                    );
                });
                defs.push(def);
            }
        });

        // fetch many2ones display_name
        _.each(_.keys(many2ones), function (name) {
            defs.push(self._fetchNameGets(x2manyList, name));
        });

        return $.when.apply($, defs);
    },
    // FORWARDPORT THIS UP TO 12.2, NOT FURTHER
    /**
     * Empty the pool of accumulated RPC requests: regroup similar requests in
     * batches and perform an RPC for each batch.
     *
     * @private
     */
    _performBatchedRPCs: function () {
        if (!this.batchedRPCsRequests.length) {
            // pool has already been processed
            return;
        }

        // reset pool of RPC requests
        var batchedRPCsRequests = this.batchedRPCsRequests;
        this.batchedRPCsRequests = [];

        // batch similar requests
        var batches = {};
        var key;
        for (var i = 0; i < batchedRPCsRequests.length; i++) {
            var request = batchedRPCsRequests[i];
            key = request.model + ',' + JSON.stringify(request.context);
            if (!batches[key]) {
                batches[key] = _.extend({}, request, {requests: [request]});
            } else {
                batches[key].ids = _.uniq(batches[key].ids.concat(request.ids));
                batches[key].fieldNames = _.uniq(batches[key].fieldNames.concat(request.fieldNames));
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
                    return _.pick(record, fieldNames);
                });
                request.def.resolve(filteredResults);
            }
        }
        function onFailure(batch, error) {
            for (var i = 0; i < batch.requests.length; i++) {
                var request = batch.requests[i];
                request.def.reject(error);
            }
        }
        for (key in batches) {
            var batch = batches[key];
            this._rpc({
                model: batch.model,
                method: 'read',
                args: [batch.ids, batch.fieldNames],
                context: batch.context,
            }).then(onSuccess.bind(null, batch)).fail(onFailure.bind(null, batch));
        }
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
        // save the RPC request
        var def = $.Deferred();
        var request = _.extend({}, params, {def: def});
        this.batchedRPCsRequests.push(request);

        if (this.disableBatchedRPCs) {
            this._performBatchedRPCs();
        } else {
            // empty the pool of RPC requests in the next tick
            setTimeout(this._performBatchedRPCs.bind(this));
        }

        return def;
    },
    /**
     * Reads data from server for all missing fields.
     *
     * @private
     * @param {Object} list a valid resource object
     * @param {interger[]} resIDs
     * @param {string[]} fieldNames to check and read if missing
     * @returns {Deferred<Object>}
     */
    _readMissingFields: function (list, resIDs, fieldNames) {
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
            var data = _.extend({}, record.data, record._changes);
            if (_.difference(fieldNames, _.keys(data)).length) {
                missingIDs.push(resId);
            }
        }

        var def;
        if (missingIDs.length && fieldNames.length) {
            // FORWARDPORT THIS UP TO 12.2, NOT FURTHER
            def = self._performRPC({
                context: list.getContext(),
                fieldNames: fieldNames,
                ids: missingIDs,
                method: 'read',
                model: list.model,
            });
        } else {
            def = $.when(_.map(missingIDs, function (id) {
                return {id:id};
            }));
        }
        return def.then(function (records) {
            _.each(resIDs, function (id) {
                var dataPoint;
                var data = _.findWhere(records, {id: id});
                if (id in list._cache) {
                    dataPoint = self.localData[list._cache[id]];
                    if (data) {
                        self._parseServerData(fieldNames, dataPoint, data);
                        _.extend(dataPoint.data, data);
                    }
                } else {
                    dataPoint = self._makeDataPoint({
                        context: list.context,
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
                _.each(list._changes, function (change) {
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
     * @returns {Deferred<Object>} resolves to the fetched group object
     */
    _readGroup: function (list, options) {
        var self = this;
        var groupByField = list.groupedBy[0];
        var rawGroupBy = groupByField.split(':')[0];
        var fields = _.uniq(list.getFieldNames().concat(rawGroupBy));
        var orderedBy = _.filter(list.orderedBy, function(order){
            return order.name === rawGroupBy || list.fields[order.name].group_operator !== undefined;
        });
        return this._rpc({
                model: list.model,
                method: 'read_group',
                fields: fields,
                domain: list.domain,
                context: list.context,
                groupBy: list.groupedBy,
                orderBy: orderedBy,
                lazy: true,
            })
            .then(function (groups) {
                var previousGroups = _.map(list.data, function (groupID) {
                    return self.localData[groupID];
                });
                list.data = [];
                list.count = 0;
                var defs = [];
                var openGroupCount = 0;

                _.each(groups, function (group) {
                    var aggregateValues = {};
                    _.each(group, function (value, key) {
                        if (_.contains(fields, key) && key !== groupByField) {
                            aggregateValues[key] = value;
                        }
                    });
                    // When a view is grouped, we need to display the name of each group in
                    // the 'title'.
                    var value = group[groupByField];
                    if (list.fields[rawGroupBy].type === "selection") {
                        var choice = _.find(list.fields[rawGroupBy].selection, function (c) {
                            return c[0] === value;
                        });
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
                    var oldGroup = _.find(previousGroups, function (g) {
                        return g.res_id === newGroup.res_id && g.value === newGroup.value;
                    });
                    if (oldGroup) {
                        // restore the internal state of the group
                        delete self.localData[newGroup.id];
                        var updatedProps = _.omit(newGroup, 'limit', 'isOpen', 'offset', 'id');
                        if (options && options.onlyGroups || oldGroup.isOpen && newGroup.groupedBy.length) {
                            // If the group is opened and contains subgroups,
                            // also keep its data to keep internal state of
                            // sub-groups
                            // Also keep data if we only reload groups' own data
                            delete updatedProps.data;
                        }
                        // set the limit such that all previously loaded records
                        // (e.g. if we are coming back to the kanban view from a
                        // form view) are reloaded
                        oldGroup.limit = oldGroup.limit + oldGroup.loadMoreOffset;
                        _.extend(oldGroup, updatedProps);
                        newGroup = oldGroup;
                    } else if (!newGroup.openGroupByDefault || openGroupCount >= self.OPEN_GROUP_LIMIT) {
                        newGroup.isOpen = false;
                    } else {
                        newGroup.isOpen = '__fold' in group ? !group.__fold : true;
                    }
                    list.data.push(newGroup.id);
                    list.count += newGroup.count;
                    if (newGroup.isOpen && newGroup.count > 0) {
                        openGroupCount++;
                        defs.push(self._load(newGroup, options));
                    }
                });
                if (options && options.keepEmptyGroups) {
                    // Find the groups that were available in a previous
                    // readGroup but are not there anymore.
                    // Note that these groups are put after existing groups so
                    // the order is not conserved. A sort *might* be useful.
                    var emptyGroupsIDs = _.difference(_.pluck(previousGroups, 'id'), list.data);
                    _.each(emptyGroupsIDs, function (groupID) {
                        list.data.push(groupID);
                        var emptyGroup = self.localData[groupID];
                        // this attribute hasn't been updated in the previous
                        // loop for empty groups
                        emptyGroup.aggregateValues = {};
                    });
                }
                return $.when.apply($, defs).then(function () {
                    if (!options || !options.onlyGroups) {
                        // generate the res_ids of the main list, being the concatenation
                        // of the fetched res_ids in each group
                        list.res_ids = _.flatten(_.map(arguments, function (group) {
                            return group ? group.res_ids : [];
                        }));
                    }
                    return list;
                });
            });
    },
    /**
     * For 'static' list, such as one2manys in a form view, we can do a /read
     * instead of a /search_read.
     *
     * @param {Object} list a valid resource object
     * @returns {Deferred<Object>} resolves to the fetched list object
     */
    _readUngroupedList: function (list) {
        var self = this;
        var def = $.when();

        // generate the current count and res_ids list by applying the changes
        list = this._applyX2ManyOperations(list);

        // for multi-pages list datapoints, we might need to read the
        // order field first to apply the order on all pages
        if (list.res_ids.length > list.limit && list.orderedBy.length) {
            if (!list.orderedResIDs) {
                var fieldNames = _.pluck(list.orderedBy, 'name');
                def = this._readMissingFields(list, _.filter(list.res_ids, _.isNumber), fieldNames);
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
                if (_.isNumber(resId)) {
                    resIDs.push(resId);
                }
            }
            return self._readMissingFields(list, resIDs, fieldNames).then(function () {
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
     * @returns {Deferred<string>} resolves to the id of the resource
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
            _.each(element._changes, function (change) {
                delete change.isNew;
            });
        }

        if (options.context !== undefined) {
            element.context = options.context;
            element.orderedBy =  options.context.orderedBy || element.orderedBy;
        }
        if (options.domain !== undefined) {
            element.domain = options.domain;
        }
        if (options.groupBy !== undefined) {
            element.groupedBy = options.groupBy;
        }
        if (options.limit !== undefined) {
            element.limit = options.limit;
        }
        if (options.offset !== undefined) {
            this._setOffset(element.id, options.offset);
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
            element.offset = _.indexOf(element.res_ids, element.res_id);
        }
        var loadOptions = _.pick(options, 'fieldNames', 'viewType');
        return this._load(element, loadOptions).then(function (result) {
            return result.id;
        });
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
        if (_.isEqual(record._specialDataCache[fieldName], value)) {
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
     * @returns {Deferred}
     */
    _searchReadUngroupedList: function (list) {
        var self = this;
        var fieldNames = list.getFieldNames();
        return this._rpc({
            route: '/web/dataset/search_read',
            model: list.model,
            fields: fieldNames,
            context: list.getContext(),
            domain: list.domain || [],
            limit: list.limit,
            offset: list.loadMoreOffset + list.offset,
            orderBy: list.orderedBy,
        })
        .then(function (result) {
            list.count = result.length;
            var ids = _.pluck(result.records, 'id');
            var data = _.map(result.records, function (record) {
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
        _.each(idsInRange, function (id) {
            if (list._cache[id]) {
                list.data.push(list._cache[id]);
            }
        });

        // display newly created record in addition to the displayed records
        if (list.limit) {
            for (var i = list.offset + list.limit; i < list.res_ids.length; i++) {
                var id = list.res_ids[i];
                var dataPointID = list._cache[id];
                if (_.findWhere(list._changes, {isNew: true, id: dataPointID})) {
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
                var data1 = _.extend({}, r1.data, r1._changes);
                var data2 = _.extend({}, r2.data, r2._changes);

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
            parent.res_ids =  _.flatten(_.map(parent.data, function (dataPointID) {
                return self.localData[dataPointID].res_ids;
            }));
            this._updateParentResIDs(parent);
        }
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
                if (_.contains(['one2many', 'many2one', 'many2many'], field.type)) {
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
            _.each(element.data, function (elemId) {
                var elem = self.localData[elemId];
                self._visitChildren(elem, fn);
            });
        }
    },
});

return BasicModel;
});
