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
 *      getEvalContext: {function},
 *      getFieldNames: {function},
 *      groupedBy: {string[]},
 *      id: {integer},
 *      isOpen: {boolean},
 *      loadMoreOffset: {integer},
 *      limit: {integer},
 *      model: {string,
 *      offset: {integer},
 *      openGroupByDefault: {boolean},
 *      orderedBy: {Object[]},
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
var Domain = require('web.Domain');
var fieldUtils = require('web.field_utils');
var session = require('web.session');

var x2ManyCommands = {
    // (0, _, {values})
    CREATE: 0,
    create: function (values) {
        return [x2ManyCommands.CREATE, false, values];
    },
    // (1, id, {values})
    UPDATE: 1,
    update: function (id, values) {
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
    /**
     * @override
     */
    init: function () {
        // this mutex is necessary to make sure some operations are done
        // sequentially, for example, an onchange needs to be completed before a
        // save is performed.
        this.mutex = new concurrency.Mutex();

        this.localData = Object.create(null);
        this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Add a default record to a list object.  This method actually make a new
     * record with the _makeDefaultRecord method, then add it to the list object.
     *
     * @param {string} listID a valid handle for a list object
     * @param {Object} [options]
     * @param {string} [options.position=top] if the new record should be added
     *   on top or on bottom of the list
     * @returns {Deferred<string>} resolves to the id of the new created record
     */
    addDefaultRecord: function (listID, options) {
        var list = this.localData[listID];
        var context = this._getContext(list);

        var position = (options && options.position) || 'top';
        var params = {
            context: context,
            fields: list.fields,
            fieldsInfo: list.fieldsInfo,
            parentID: list.id,
            viewType: list.viewType,
        };
        return this._makeDefaultRecord(list.model, params).then(function (id) {
            list.count++;
            list._changes = list._changes || list.data.slice(0);
            if (position === 'top') {
                list._changes.unshift(id);
            } else {
                list._changes.push(id);
            }
            return id;
        });
    },
    /**
     * Delete a list of records, then, if a parentID is given, reload the
     * parent.
     *
     * @todo we should remove the deleted records from the localData
     * @todo why can't we infer modelName?
     *
     * @param {string[]} recordIds list of local resources ids. They should all
     *   be of type 'record', and of the same model
     * @param {string} modelName
     * @returns {Deferred}
     */
    deleteRecords: function (recordIds, modelName) {
        var self = this;
        var records = _.map(recordIds, function (id) { return self.localData[id]; });
        return this._rpc({
                model: modelName,
                method: 'unlink',
                args: [_.pluck(records, 'res_id')],
                context: session.user_context, // todo: combine with view context
            })
            .then(function () {
                _.each(records, function (record) {
                    record.res_ids.splice(record.offset, 1);
                    record.res_id = record.res_ids[record.offset];
                    record.count--;
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
        var rollback = options.rollback || isNew;
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
        });
    },
    /**
     * Duplicate a record (by calling the 'copy' route)
     *
     * @param {string} recordID id for a local resource
     * @returns {Deferred -> string} resolves to the id of duplicate record
     */
    duplicateRecord: function (recordID) {
        var self = this;
        var record = this.localData[recordID];
        return this._rpc({
                model: record.model,
                method: 'copy',
                args: [record.data.id],
                context: this._getContext(record),
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
     * @param {boolean} [options.noUnsetNumeric=false] if true, will set numeric
     *   values to 0 if not set
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
                if (options.noUnsetNumeric) {
                    if (field.type === 'float' ||
                        field.type === 'integer' ||
                        field.type === 'monetary') {
                        data[fieldName] = data[fieldName] || 0;
                    }
                }

                // get relational datapoint
                if (field.type === 'many2one') {
                    if (options.raw) {
                        relDataPoint = this.localData[data[fieldName]];
                        data[fieldName] = relDataPoint ? relDataPoint.res_id : false;
                    } else {
                        data[fieldName] = this.get(data[fieldName]) || false;
                    }
                }
                if (field.type === 'one2many' || field.type === 'many2many') {
                    if (options.raw) {
                        relDataPoint = this.localData[data[fieldName]];
                        var relData = relDataPoint._changes || relDataPoint.data;
                        var ids = _.map(relData, function (id) {
                            return self.localData[id].res_id;
                        });
                        data[fieldName] = ids;
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
                fields: element.fields,
                fieldsInfo: element.fieldsInfo,
                getContext: element.getContext,
                getDomain: element.getDomain,
                getEvalContext: element.getEvalContext,
                getFieldNames: element.getFieldNames,
                id: element.id,
                limit: element.limit,
                model: element.model,
                offset: element.offset,
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

        // here, type === 'list'
        var listData, listCount, resIDs;
        if (element._changes) {
            listData = element._changes;
            listCount = listData.length;
            resIDs = _.map(listData, function (elemID) {
                return self.localData[elemID].res_id;
            });
        } else {
            listData = element.data;
            listCount = element.count;
            resIDs = element.res_ids;
        }
        listData = _.map(listData, function (elemID) {
            return self.get(elemID, options);
        });
        var list = {
            aggregateValues: _.extend({}, element.aggregateValues),
            context: _.extend({}, element.context),
            count: listCount,
            data: listData,
            domain: element.domain.slice(0),
            fields: element.fields,
            getContext: element.getContext,
            getDomain: element.getDomain,
            getEvalContext: element.getEvalContext,
            getFieldNames: element.getFieldNames,
            groupedBy: element.groupedBy,
            id: element.id,
            isOpen: element.isOpen,
            limit: element.limit,
            model: element.model,
            offset: element.offset,
            orderedBy: element.orderedBy,
            res_id: element.res_id,
            res_ids: resIDs,
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
     * @returns {Deferred -> string} resolves to a local id, or handle
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
                                type: 'record',
                            });
                            dataPoint.data.push(recordDP.id);
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
     * @returns {string[]} list of changed fields
     */
    notifyChanges: function (record_id, changes) {
        return this.mutex.exec(this._applyChange.bind(this, record_id, changes));
    },
    /**
     * Reload all data for a given resource
     *
     * @param {string} id local id for a resource
     * @param {Object} [options]
     * @param {boolean} [options.keepChanges=false] if true, doesn't discard the
     *   changes on the record before reloading it
     * @returns {Deferred -> string} resolves to the id of the resource
     */
    reload: function (id, options) {
        options = options || {};
        var element = this.localData[id];

        if (element.type === 'record') {
            if ('currentId' in options && !options.currentId) {
                var params = {
                    context: element.context,
                    fieldsInfo: element.fieldsInfo,
                    fields: element.fields,
                    viewType: element.viewType,
                };
                return this._makeDefaultRecord(element.model, params);
            }
            if (!options.keepChanges) {
                this.discardChanges(id);
            }
        }

        if (options.context !== undefined) {
            element.context = options.context;
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
     * In some case, we may need to remove an element from a list, without going
     * through the notifyChanges machinery.  The motivation for this is when the
     * user click on 'Add an item' in a field one2many with a required field,
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
        parent._changes = _.without(parent._changes, elementID);
    },
    /**
     * Save a local resource, if needed.  This is a complicated operation,
     * - it needs to check all changes,
     * - generate commands for x2many fields,
     * - call the /create or /write method according to the record status
     * - After that, it has to reload all data, in case something changed,
     *   server side.
     *
     * @param {string} record_id local resource
     * @param {Object} [options]
     * @param {boolean} [options.reload=true] if true, data will be reloaded
     * @param {boolean} [options.savePoint=false] if true, the record will only
     *   be 'locally' saved: its changes written in a _savePoint key that can
     *   be restored later by call discardChanges with option rollback to true
     * @returns {Deferred}
     */
    save: function (record_id, options) {
        var self = this;
        return this.mutex.exec(function () {
            options = options || {};
            var record = self.localData[record_id];
            if (options.savePoint) {
                self._visitChildren(record, function (rec) {
                    var newValue = rec._changes || rec.data;
                    if (newValue instanceof Array) {
                        rec._savePoint = newValue.slice(0);
                    } else {
                        rec._savePoint = _.extend({}, newValue);
                    }
                });
                return $.when();
            }
            var shouldReload = 'reload' in options ? options.reload : true;
            var method = self.isNew(record_id) ? 'create' : 'write';
            if (record._changes) {
                // id never changes, and should not be written
                delete record._changes.id;
            }
            var changes = self._generateChanges(record);

            if (method === 'create') {
                var fieldNames = record.getFieldNames();
                _.each(fieldNames, function (name) {
                    if (changes[name] === null) {
                        delete changes[name];
                    }
                });
            }

            // in the case of a write, only perform the RPC if there are changes to save
            if (method === 'create' || Object.keys(changes).length) {
                var args = method === 'write' ? [[record.data.id], changes] : [changes];
                return self._rpc({
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

                        // Update the data directly or reload them
                        var def;
                        if (shouldReload) {
                            def = self._fetchRecord(record);
                        } else {
                            _.extend(record.data, record._changes);
                        }

                        // Erase changes as they have been applied
                        record._changes = {};
                        record._isDirty = false;

                        return def;
                    });
            } else {
                return $.when(record_id);
            }
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
        record.fields = _.defaults(record.fields, viewInfo.fields);
        record.fieldsInfo = _.defaults(record.fieldsInfo, viewInfo.fieldsInfo);
    },
    /**
     * For list resources, this changes the orderedBy key, then performs the
     * sort directly, in javascript.  This is used for sorting static datasets,
     * such as a one2many in a form view. For dynamic datasets, such as a list
     * view, this method will be called, but then the sort will be ignored since
     * we will reload data.
     *
     * @todo don't sort in js when we reload data anyway
     *
     * @param {string} list_id id for the list resource
     * @param {string} fieldName valid field name
     * @returns {this} so we can chain call this method
     */
    setSort: function (list_id, fieldName) {
        var list = this.localData[list_id];
        if (list.type === 'record') {
            return;
        }
        list.offset = 0;
        if (list.orderedBy.length === 0) {
            list.orderedBy.push({name: fieldName, asc: true});
        } else if (list.orderedBy[0].name === fieldName){
            list.orderedBy[0].asc = !list.orderedBy[0].asc;
        } else {
            var orderedBy = _.reject(list.orderedBy, function (o) {
                return o.name === fieldName;
            });
            list.orderedBy = [{name: fieldName, asc: true}].concat(orderedBy);
        }
        this._sortList(list);
        return this;
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
            .then(this.reload.bind(this, parentID));

    },
    /**
     * Toggle (open/close) a group in a grouped list, then fetches relevant
     * data
     *
     * @param {string} groupId
     * @returns {Deferred -> string} resolves to the group id
     */
    toggleGroup: function (groupId) {
        var group = this.localData[groupId];
        if (group.isOpen) {
            group.isOpen = false;
            group.data = [];
            group.offset = 0;
            return $.when(groupId);
        }
        if (!group.isOpen) {
            group.isOpen = true;
            var def;
            if (group.count > 0) {
                def = this._load(group);
            }
            return $.when(def).then(function () {
                return groupId;
            });
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * This method is the private version of notifyChanges.  Unlike
     * notifyChanges, it is not protected by a mutex.  Every changes from the
     * user to the model go through this method.
     *
     * @param {string} recordID
     * @param {Object} changes
     * @returns {Deferred}
     */
    _applyChange: function (recordID, changes) {
        var self = this;
        var record = this.localData[recordID];
        var field;
        var defs = [];
        record._changes = record._changes || {};
        record._isDirty = true;

        // apply changes to local data
        for (var fieldName in changes) {
            field = record.fields[fieldName];
            if (field.type === 'one2many' || field.type === 'many2many') {
                defs.push(this._applyX2ManyChange(record, fieldName, changes[fieldName]));
            } else if (field.type === 'many2one') {
                defs.push(this._applyMany2OneChange(record, fieldName, changes[fieldName]));
            } else {
                record._changes[fieldName] = changes[fieldName];
            }
        }

        return $.when.apply($, defs).then(function () {
            var onChangeFields = []; // the fields that have changed and that have an on_change
            for (var fieldName in changes) {
                field = record.fields[fieldName];
                if (field.onChange) {
                    var isX2Many = field.type === 'one2many' || field.type === 'many2many';
                    if (!isX2Many || (self._isX2ManyValid(record._changes[fieldName] || record.data[fieldName]))) {
                        onChangeFields.push(fieldName);
                    }
                }
            }
            var onchangeDef;
            if (onChangeFields.length) {
                onchangeDef = self._performOnChange(record, onChangeFields).then(function (result) {
                    delete record._warning;
                    return _.keys(changes).concat(Object.keys(result && result.value || {}));
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
     * Apply a many2one onchange.  There is a need for this function because the
     * server only gives an id when a onchange modifies a many2one field.  For
     * this reason, we need (sometimes) to do a /name_get to fetch a
     * display_name.
     *
     * @param {Object} record
     * @param {string} fieldName
     * @param {Object} [data]
     * @returns {Deferred}
     */
    _applyMany2OneChange: function (record, fieldName, data) {
        var self = this;
        if (!data) {
            record._changes[fieldName] = false;
            return $.when();
        }
        var rel_data = _.pick(data, 'id', 'display_name');
        var def;
        if (rel_data.display_name === undefined) {
            var field = record.fields[fieldName];
            // TODO: refactor this to use _fetchNameGet
            def = this._rpc({
                    model: field.relation,
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
                modelName: record.fields[fieldName].relation,
            });
            record._changes[fieldName] = rec.id;
        });
    },
    /**
     * Applies the result on an onchange RPC on a record.
     *
     * @private
     * @param {Object} values the result of the onchange RPC (a mapping of
     *   fieldnames to their value)
     * @param {Object} record
     * @returns {Deferred}
     */
    _applyOnChange: function (values, record) {
        var self = this;
        var defs = [];
        var rec;
        record._changes = record._changes || {};
        _.each(values, function (val, name) {
            var field = record.fields[name];
            if (!field) {
                return; // ignore changes of unknown fields
            }

            if (field.type === 'many2one' ) {
                var id = false;
                // in some case, the value returned by the onchange can
                // be false (no value), so we need to avoid creating a
                // local record for that.
                if (val) {
                    // when the value isn't false, it can be either
                    // an array [id, display_name] or just an id.
                    var data = _.isArray(val) ?
                        {id: val[0], display_name: val[1]} :
                        {id: val};
                    rec = self._makeDataPoint({
                        context: record.context,
                        data: data,
                        modelName: field.relation,
                    });
                    id = rec.id;
                }
                record._changes[name] = id;
            } else if (field.type === 'one2many' || field.type === 'many2many') {
                var listId = record._changes[name] || record.data[name];
                var list;
                if (listId) {
                    list = self.localData[listId];
                } else {
                    var fieldInfo = record.fieldsInfo[record.viewType][name];
                    if (!fieldInfo) {
                        return; //ignore changes of x2many not in view
                    }
                    list = self._makeDataPoint({
                        fieldsInfo: fieldInfo.fieldsInfo,
                        modelName: field.relation,
                        type: 'list',
                        viewtype: fieldInfo.viewType,
                    });
                }
                record._changes[name] = list.id;
                var shouldLoad = false;
                _.each(val, function (command) {
                    if (command[0] === 0 || command[0] === 1) {
                        // CREATE or UPDATE
                        var params = {
                            context: list.context,
                            fields: list.fields,
                            fieldsInfo: list.fieldsInfo,
                            modelName: list.model,
                            parentID: list.id,
                            viewType: list.viewType,
                        };
                        if (command[0] === 1) {
                            params.res_id = command[1];
                        }
                        rec = self._makeDataPoint(params);
                        list._changes.push(rec.id);
                        defs.push(self._applyOnChange(command[2], rec));
                    } else if (command[0] === 4) {
                        // LINK TO
                        list.res_ids.push(command[1]);
                        list.count++;
                        shouldLoad = true;
                    } else if (command[0] === 5) {
                        // DELETE ALL
                        list._changes = [];
                    }
                });
                if (shouldLoad) {
                    var def = self._readUngroupedList(list).then(function () {
                        list._changes = list.data;
                    });
                    defs.push(def);
                }
            } else if (field.type === 'date') {
                // process data: convert into a moment instance
                record._changes[name] = fieldUtils.parse.date(val);
            } else if (field.type === 'datetime') {
                // process datetime: convert into a moment instance
                record._changes[name] = fieldUtils.parse.datetime(val);
            } else {
                record._changes[name] = val;
            }
        });
        return $.when.apply($, defs);
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
     * @returns {Deferred}
     */
    _applyX2ManyChange: function (record, fieldName, command) {
        var self = this;
        var list = this.localData[record._changes[fieldName] || record.data[fieldName]];
        var field = record.fields[fieldName];
        var fieldInfo = record.fieldsInfo[record.viewType][fieldName];
        var view = fieldInfo.views && fieldInfo.views[fieldInfo.mode];
        var rec;
        var defs = [];
        list._changes = list._changes || list.data.slice(0);

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
                list._changes.push(newRecord.id);
                break;
            case 'ADD_M2M':
                // force to use link command instead of create command
                list._forceM2MLink = true;
                // handle multiple add: command[2] may be a dict of values (1
                // record added) or an array of dict of values
                var data = _.isArray(command.ids) ? command.ids : [command.ids];
                var list_records = {};
                _.each(data, function (d) {
                    rec = self._makeDataPoint({
                        context: record.context,
                        modelName: field.relation,
                        fields: view ? view.fields : fieldInfo.relatedFields,
                        fieldsInfo: view ? view.fieldsInfo : fieldInfo.fieldsInfo,
                        res_id: d.id,
                        viewType: view ? view.type : fieldInfo.viewType,
                    });
                    list_records[d.id] = rec;
                    list._changes.push(rec.id);
                });
                // read list's records as we only have their ids and optionally their display_name
                // (we can't use function readUngroupedList because those records are only in the
                // _changes so this is a very specific case)
                // this could be optimized by registering the fetched records in the list's _cache
                // so that if a record is removed and then re-added, it won't be fetched twice
                var fieldNames = list.getFieldNames();
                if (fieldNames.length) {
                    var def = this._rpc({
                        model: list.model,
                        method: 'read',
                        args: [_.pluck(data, 'id'), fieldNames]
                    }).then(function (records) {
                        _.each(records, function (record) {
                            list_records[record.id].data = record;
                            self._parseServerData(fieldNames, list.fields, record);
                        });
                        return self._fetchX2ManysBatched(list);
                    });
                    defs.push(def);
                }
                break;
            case 'CREATE':
                if (command.data) {
                    defs.push(this.addDefaultRecord(list.id).then(function (id) {
                        return self._applyChange(id, command.data);
                    }));
                } else {
                    defs.push(this.addDefaultRecord(list.id, {position: command.position}));
                }
                break;
            case 'UPDATE':
                defs.push(this._applyChange(command.id, command.data));
                break;
            case 'REMOVE':
                list._changes = _.difference(list._changes, command.ids);
                break;
            case 'REPLACE_WITH':
                // this is certainFly not optimal... and not sure that it is
                // correct if some ids are added and some other are removed
                var currentData = _.map(list._changes, function (localId) {
                    return self.localData[localId];
                });
                var currentIds = _.pluck(currentData, 'res_id');
                var newIds = _.difference(command.ids, currentIds);
                var removedIds = _.difference(currentIds, command.ids);
                var addDef, removedDef, values;
                if (newIds.length) {
                    values = _.map(newIds, function (id) {
                        return {id: id};
                    });
                    addDef = this._applyX2ManyChange(record, fieldName, {
                        operation: 'ADD_M2M',
                        ids: values
                    });
                }
                if (removedIds.length) {
                    values = _.filter(currentData, function (dataPoint) {
                        return _.contains(removedIds, dataPoint.res_id);
                    });
                    removedDef = this._applyX2ManyChange(record, fieldName, {
                        operation: 'REMOVE',
                        ids: _.pluck(values, 'id'),
                    });
                }
                return $.when(addDef, removedDef);
        }

        return $.when.apply($, defs);
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
     * @returns {Object} an onchange spec
     */
    _buildOnchangeSpecs: function (record) {
        // TODO: replace this function by some generic tree function in utils
        var specs = {};
        _.each(record.getFieldNames(), function (name) {
            var field = record.fields[name];
            var fieldInfo = record.fieldsInfo[record.viewType][name];
            specs[name] = (field.onChange) || "";
            _.each(fieldInfo.views, function (view) {
                _.each(view.fieldsInfo[view.type], function (field, subname) {
                    specs[name + '.' + subname] = (view.fields[subname].onChange) || "";
                });
            });
        });
        return specs;
    },
    /**
     * Fetch all name_gets for the many2ones in a group
     *
     * @param {Object} group a valid resource object
     * @returns {Deferred}
     */
    _fetchMany2OneGroup: function (group) {
        var ids = _.uniq(_.pluck(group, 'res_id'));

        return this._rpc({
                model: group[0].model,
                method: 'name_get',
                args: [ids],
                context: group[0].context
            })
            .then(function (name_gets) {
                _.each(group, function (record) {
                    var nameGet = _.find(name_gets, function (n) { return n[0] === record.res_id;});
                    record.data.display_name = nameGet[1];
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
    _fetchNameGets: function (list, fieldName) {
        var self = this;
        var model;
        var records = [];
        var ids = _.map(list._changes || list.data, function (localId) {
            var record = self.localData[localId];
            var data = record._changes || record.data;
            var many2oneId = data[fieldName];
            var many2oneRecord = self.localData[many2oneId];
            records.push(many2oneRecord);
            model = many2oneRecord.model;
            return many2oneRecord.res_id;
        });
        return this._rpc({
                model: model,
                method: 'name_get',
                args: [ids],
                context: list.context,
            })
            .then(function (name_gets) {
                for (var i = 0; i < name_gets.length; i++) {
                    records[i].data.display_name = name_gets[i][1];
                }
            });
    },
    /**
     * For a given resource of type 'record', fetch all data.
     *
     * @param {Object} record local resource
     * @param {Object} [options]
     * @param {string[]} [options.fieldNames] the list of fields to fetch. If
     *   not given, fetch all the fields in record.fieldNames (+ display_name)
     * @param {string} [optinos.viewType] the type of view for which the record
     *   is fetched (usefull to load the adequate fields), by defaults, uses
     *   record.viewType
     * @returns {Deferred -> Object} resolves to the record
     */
    _fetchRecord: function (record, options) {
        var self = this;
        var fieldNames = options && options.fieldNames ||
                         _.uniq(record.getFieldNames().concat(['display_name']));
        return this._rpc({
                model: record.model,
                method: 'read',
                args: [[record.res_id], fieldNames],
                context: _.extend({}, record.context, {bin_size: true}),
            })
            .then(function (result) {
                result = result[0];
                record.data = _.extend({}, record.data, result);
            })
            .then(function () {
                self._parseServerData(fieldNames, record.fields, record.data);
            })
            .then(function () {
                return self._fetchX2Manys(record, options).then(function () {
                    return self._postprocess(record, options);
                });
            });
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
                if (!relatedRecord) {
                    return;
                }
                toBeFetched.push(relatedRecord);
            }
        });

        // group them by model and context. Using the context as key is
        // necessary to make sure the correct context is used for the rpc;
        var groups = _.groupBy(toBeFetched, function (rec) {
            return [rec.model, JSON.stringify(rec.context)].join();
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
            var localID = record._changes && record._changes[fieldName] || record.data[fieldName];
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
        var domainValue = record._changes && record._changes[fieldName] || record.data[fieldName];

        // avoid rpc if not necessary
        var hasChanged = this._saveSpecialDataCache(record, fieldName, {
            context: context,
            domainModel: domainModel,
            domainValue: domainValue,
        });
        if (!hasChanged) {
            return $.when();
        }

        var def = $.Deferred();

        this._rpc({
                model: domainModel,
                method: 'search_count',
                args: [Domain.prototype.stringToArray(domainValue)],
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
     * @returns {Deferred -> Object} resolves to the fecthed list
     */
    _fetchUngroupedList: function (list) {
        var self = this;
        var def;
        if (list.static) {
            def = this._readUngroupedList(list);
        } else {
            def = this._searchReadUngroupedList(list);
        }
        return def.then(function () {
            return self._fetchX2ManysBatched(list);
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
        var fieldNames = options && options.fieldNames || record.getFieldNames();
        var viewType = options && options.viewType || record.viewType;
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
                        return self._fetchX2ManysBatched(list);
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
        var data = list._changes || list.data;
        var x2mRecords = [];

        // step 1: collect ids
        var ids = [];
        _.each(data, function (dataPoint) {
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
                context: {}, // FIXME
            });
        } else {
            def = $.when(_.map(ids, function (id) {
                return {id:id};
            }));
        }
        return def.then(function (results) {
            // step 3: assign values to correct datapoints
            var dataPoints = _.map(results, function (result) {
                return self._makeDataPoint({
                    modelName: field.relation,
                    data: result,
                    fields: fields,
                    fieldsInfo: fieldsInfo,
                    viewType: viewType,
                });
            });

            _.each(x2mRecords, function (record) {
                var m2mList = self.localData[record.data[fieldName]];

                m2mList.data = [];
                _.each(m2mList.res_ids, function (res_id) {
                    var dataPoint = _.find(dataPoints, function (d) {
                        return d.res_id === res_id;
                    });
                    m2mList.data.push(dataPoint.id);
                    m2mList.count++;
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
     * @returns {Object} a map from changed fields to their new value
     */
    _generateChanges: function (record) {
        var changes = _.extend({}, record._changes);
        var commands = this._generateX2ManyCommands(record, true);
        for (var fieldName in record.fields) {
            var type = record.fields[fieldName].type;
            if (type === 'one2many' || type === 'many2many') {
                if (commands[fieldName].length) { // replace localId by commands
                    changes[fieldName] = commands[fieldName];
                } else { // no command -> no change for that field
                    delete changes[fieldName];
                }
            } else if (type === 'many2one' && fieldName in changes) {
                var value = changes[fieldName];
                changes[fieldName] = value ? this.localData[value].res_id : false;
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
     * @returns {Object} the data
     */
    _generateOnChangeData: function (record) {
        var commands = this._generateX2ManyCommands(record, false);
        var data = _.extend(this.get(record.id, {raw: true}).data, commands);

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
     * @param {boolean} [changesOnly=false] if true, only generates commands for
     *   fields that have changed
     * @returns {Object} a map from some field names to commands
     */
    _generateX2ManyCommands: function (record, changesOnly) {
        var self = this;
        var commands = {};
        var data = _.extend({}, record.data, record._changes);
        var type;
        for (var fieldName in record.fields) {
            type = record.fields[fieldName].type;

            if (type === 'many2many' || type === 'one2many') {
                commands[fieldName] = [];
                if (!data[fieldName]) {
                    // skip if this field is empty
                    continue;
                }
                var list = this.localData[data[fieldName]];
                if (changesOnly && !list._changes) {
                    // if only changes are requested, skip if there is no change
                    continue;
                }
                var relData = _.map(list._changes || list.data, function (localId) {
                    return self.localData[localId];
                });
                var relIds = _.pluck(relData, 'res_id');
                if (type === 'many2many' || list._forceM2MLink) {
                    // deliberately generate a single 'replace' command instead
                    // of a 'delete' and a 'link' commands with the exact diff
                    // because 1) performance-wise it doesn't change anything
                    // and 2) to guard against concurrent updates (policy: force
                    // a complete override of the actual value of the m2m)
                    commands[fieldName].push(x2ManyCommands.replace_with(relIds));
                    // generate update commands for records that have been
                    // updated (it may happen with editable lists)
                    _.each(relData, function (relRecord) {
                        if (!_.isEmpty(relRecord._changes)) {
                            var changes = self._generateChanges(relRecord);
                            var command = x2ManyCommands.update(relRecord.res_id, changes);
                            commands[fieldName].push(command);
                        }
                    });
                } else if (type === 'one2many') {
                    var removedIds = _.difference(list.res_ids, relIds);
                    var addedIds = _.difference(relIds, list.res_ids);
                    var keptIds = _.intersection(list.res_ids, relIds);

                    // the didChange variable keeps track of the fact that at
                    // least one id was updated
                    var didChange = false;
                    var changes, command, relRecord;
                    for (var i = 0; i < relIds.length; i++) {
                        if (_.contains(keptIds, relIds[i])) {
                            // this is an id that already existed
                            relRecord = _.findWhere(relData, {res_id: relIds[i]});
                            if (!_.isEmpty(relRecord._changes)) {
                                changes = this._generateChanges(relRecord);
                                command = x2ManyCommands.update(relRecord.res_id, changes);
                                didChange = true;
                            } else {
                                command = x2ManyCommands.link_to(relIds[i]);
                            }
                            commands[fieldName].push(command);
                        } else if (_.contains(addedIds, relIds[i])) {
                            // this is a new id
                            relRecord = _.findWhere(relData, {res_id: relIds[i]});
                            changes = this._generateChanges(relRecord);
                            commands[fieldName].push(x2ManyCommands.create(changes));
                        }
                    }
                    if (changesOnly && !didChange && addedIds.length === 0 && removedIds.length === 0) {
                        // in this situation, we have no changed ids, no added
                        // ids and no removed ids, so we can safely ignore the
                        // last changes
                        commands[fieldName] = [];
                    }
                    // add delete commands
                    for (i = 0; i < removedIds.length; i++) {
                        commands[fieldName].push(x2ManyCommands.delete(removedIds[i]));
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
     *        if true and fieldName given in options, the element's context
     *        is added to the context
     * @returns {Object} the evaluated context
     */
    _getContext: function (element, options) {
        options = options || {};
        var context = new Context(session.user_context);
        context.set_eval_context(this._getEvalContext(element));

        if (options.full || !options.fieldName) {
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
            var viewType = options.viewType || element.viewType;
            var fieldInfo = element.fieldsInfo[viewType][options.fieldName];
            if (fieldInfo && fieldInfo.domain) {
                return Domain.prototype.stringToArray(
                    fieldInfo.domain,
                    this._getEvalContext(element)
                );
            }
            var fieldParams = element.fields[options.fieldName];
            if (fieldParams.domain) {
                return Domain.prototype.stringToArray(
                    fieldParams.domain,
                    this._getEvalContext(element)
                );
            }
            return [];
        }

        return Domain.prototype.stringToArray(
            element.domain,
            this._getEvalContext(element)
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
     * @returns {Object}
     */
    _getEvalContext: function (element) {
        var evalContext = this.get(element.id, {raw: true, noUnsetNumeric: true}).data;
        evalContext.active_model = element.model;
        evalContext.id = evalContext.id || false;
        evalContext.active_id = evalContext.id;
        evalContext.active_ids = evalContext.id ? [evalContext.id] : [];
        if (element.parentID) {
            var parent = this.get(element.parentID, {raw: true});
            if (parent.type === 'list' && this.localData[element.parentID].parentID) {
                parent = this.get(this.localData[element.parentID].parentID, {raw: true});
            }
            _.extend(evalContext, {parent: parent.data});
        }
        return _.extend({}, session.user_context, element.context, evalContext);
    },
    /**
     * Returns the list of field names of the given element according to its
     * default view type.
     *
     * @param {Object} element an element from the localData
     * @returns {string[]} the list of field names
     */
    _getFieldNames: function (element) {
        var fieldsInfo = element.fieldsInfo;
        return Object.keys(fieldsInfo && fieldsInfo[element.viewType] || {});
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
     *   assumed to be a list element for a one2many
     * @returns {boolean}
     */
    _isX2ManyValid: function (id) {
        var self = this;
        var isValid = true;
        var element = this.get(id, {raw: true});
        _.each(element.getFieldNames(), function (fieldName) {
            var field = element.fields[fieldName];
            _.each(element.data, function (rec) {
                if (field.required && !self._isFieldSet(rec.data[fieldName], field.type)) {
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
     * @returns {Deferred}
     */
    _load: function (dataPoint, options) {
        if (dataPoint.type === 'record') {
            return this._fetchRecord(dataPoint, options);
        }
        if (dataPoint.type === 'list' && dataPoint.groupedBy.length) {
            return this._readGroup(dataPoint);
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
     * @param {Object} [params.fieldsInfo={}] contains the fieldInfo of each field
     * @param {Array} [params.fieldNames] the name of fields to load, the list
     *   of all fields by default
     * @param {Object} params.fields contains the description of each field
     * @returns {Object} the resource created
     */
    _makeDataPoint: function (params) {
        var type = params.type || ('domain' in params && 'list') || 'record';
        var res_id, value;
        var res_ids = params.res_ids || [];
        if (type === 'record') {
            res_id = params.res_id || (params.data && params.data.id) || _.uniqueId('virtual_');
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
            aggregateValues: params.aggregateValues || {},
            context: params.context || {},
            count: params.count || res_ids.length,
            data: params.data || (type === 'record' ? {} : []),
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
            parentID: params.parentID,
            rawContext: params.rawContext,
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

        dataPoint.getContext = this._getContext.bind(this, dataPoint);
        dataPoint.getDomain = this._getDomain.bind(this, dataPoint);
        dataPoint.getEvalContext = this._getEvalContext.bind(this, dataPoint);
        dataPoint.getFieldNames = this._getFieldNames.bind(this, dataPoint);

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
     * @param {Object} params.context the context for the new record
     * @param {Object} params.fieldsInfo contains the fieldInfo of each view,
     *   for each field
     * @param {Object} params.fields contains the description of each field
     * @param {Object} params.context the context for the new record
     * @param {string} params.viewType the key in fieldsInfo of the fields to load
     * @returns {Deferred -> string} resolves to the id for the created resource
     */
    _makeDefaultRecord: function (modelName, params) {
        var self = this;
        var fieldNames = Object.keys(params.fieldsInfo[params.viewType]);
        var fields_key = _.without(fieldNames, '__last_update');

        return this._rpc({
                model: modelName,
                method: 'default_get',
                args: [fields_key],
                context: params.context,
            })
            .then(function (result) {
                // fill default values for missing fields
                for (var i = 0; i < fieldNames.length; i++) {
                    var fieldName = fieldNames[i];
                    if (!(fieldName in result)) {
                        var field = params.fields[fieldName];
                        if (field.type === 'one2many' || field.type === 'many2many') {
                            result[fieldName] = [];
                        } else {
                            result[fieldName] = null;
                        }
                    }
                }

                var data = {};
                var record = self._makeDataPoint({
                    modelName: modelName,
                    data: data,
                    fields: params.fields,
                    fieldsInfo: params.fieldsInfo,
                    context: params.context,
                    parentID: params.parentID,
                    res_ids: params.res_ids,
                    viewType: params.viewType,
                });

                var defs = [];
                _.each(fieldNames, function (name) {
                    var field = params.fields[name];
                    data[name] = null;
                    record._changes = record._changes || {};
                    if (field.type === 'many2one' && result[name]) {
                        var rec = self._makeDataPoint({
                            context: record.context,
                            data: {id: result[name]},
                            modelName: field.relation,
                        });
                        record._changes[name] = rec.id;
                    } else if (field.type === 'one2many' || field.type === 'many2many') {
                        var fieldInfo = record.fieldsInfo[record.viewType][name];
                        var view = fieldInfo.views && fieldInfo.views[fieldInfo.mode];
                        var fieldsInfo = view ? view.fieldsInfo : fieldInfo.fieldsInfo;
                        var fields = view ? view.fields : fieldInfo.relatedFields;
                        var viewType = view ? view.type : fieldInfo.viewType;

                        var x2manyList = self._makeDataPoint({
                            context: record.context,
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
                        record._changes[name] = x2manyList.id;
                        var many2ones = {};
                        var r;
                        _.each(result[name], function (value) {
                            if (_.isArray(value)) {
                                // value is a command
                                if (value[0] === 0) {
                                    // CREATE
                                    r = self._makeDataPoint({
                                        modelName: x2manyList.model,
                                        context: x2manyList.context,
                                        fieldsInfo: fieldsInfo,
                                        fields: fields,
                                        viewType: viewType,
                                    });
                                    x2manyList._changes = x2manyList._changes || [];
                                    x2manyList._changes.push(r.id);
                                    r._changes = value[2];

                                    // this is necessary so the fields are initialized
                                    for (var fieldName in value[2]) {
                                        r.data[fieldName] = null;
                                    }

                                    for (var name in r._changes) {
                                        var isFieldInView = name in r.fields;
                                        if (isFieldInView && r.fields[name].type === 'many2one') {
                                            var rec = self._makeDataPoint({
                                                context: r.context,
                                                modelName: r.fields[name].relation,
                                                data: {id: r._changes[name]}
                                            });
                                            r._changes[name] = rec.id;
                                            many2ones[name] = true;
                                        }
                                    }
                                }
                                if (value[0] === 6) {
                                    // REPLACE_WITH
                                    x2manyList.res_ids = value[2];
                                    x2manyList.count = x2manyList.res_ids.length;
                                    defs.push(self._readUngroupedList(x2manyList));
                                }
                            } else {
                                // value is an id
                                r = self._makeDataPoint({
                                    modelName: x2manyList.model,
                                    context: x2manyList.context,
                                    fieldsInfo: fieldsInfo,
                                    fields: fields,
                                    res_id: value,
                                    viewType: viewType,
                                });
                                if (!x2manyList._changes) {
                                    x2manyList._changes = [];
                                }
                                x2manyList._changes.push(r.id);
                            }
                        });

                        // fetch many2ones display_name
                        _.each(_.keys(many2ones), function (name) {
                            defs.push(self._fetchNameGets(x2manyList, name));
                        });
                    } else if (field.type === 'date') {
                        // process date: convert into a moment instance
                        record._changes[name] = fieldUtils.parse.date(result[name], field, {isUTC: true});
                    } else if (field.type === 'datetime') {
                        // process datetime: convert into a moment instance
                        record._changes[name] = fieldUtils.parse.datetime(result[name], field, {isUTC: true});
                    } else {
                        record._changes[name] = result[name];
                    }
                });
                return $.when.apply($, defs)
                    .then(function () {
                        var shouldApplyOnchange = false;
                        var field;
                        for (var field_name in record.data) {
                            field = record.fields[field_name];
                            if (field.onChange) {
                                shouldApplyOnchange = true;
                            }
                        }
                        if (shouldApplyOnchange) {
                            return self._performOnChange(record, fields_key).then(function () {
                                if (record._warning) {
                                    return $.Deferred().reject();
                                }
                            });
                        } else {
                            return $.when();
                        }
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
                        self.save(record.id, {savePoint: true})

                        return record.id;
                    });
            });
    },
    /**
     * parse the server values to javascript framwork
     *
     * @param {[string]} fieldNames
     * @param {Object} fields
     * @param {Object} record
     */
    _parseServerData: function (fieldNames, fields, record) {
        var self = this;
        _.each(fieldNames, function (fieldName) {
            var field = fields[fieldName];
            var val = record[fieldName];
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
                    });
                    record[fieldName] = r.id;
                } else {
                    // no value for the many2one
                    record[fieldName] = false;
                }
            } else if (field.type === 'date') {
                // process data: convert into a moment instance
                record[fieldName] = fieldUtils.parse.date(val, field, {isUTC: true});
            } else if (field.type === 'datetime') {
                // process datetime: convert into a moment instance
                record[fieldName] = fieldUtils.parse.datetime(val, field, {isUTC: true});
            }
        });
    },
    /**
     * This method is quite important: it is supposed to perform the /onchange
     * rpc and apply the result.
     *
     * @param {Object} record
     * @param {string[]} fields changed fields
     * @returns {Deferred} The returned deferred can fail, in which case the
     *   fail value will be the warning message received from the server
     */
    _performOnChange: function (record, fields) {
        var self = this;
        var onchange_spec = this._buildOnchangeSpecs(record);
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
        var currentData = this._generateOnChangeData(record);

        return self._rpc({
                model: record.model,
                method: 'onchange',
                args: [idList, currentData, fields, onchange_spec, context],
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
     * @param {Object} record
     * @returns {Deferred -> Object} resolves to the finished resource
     */
    _postprocess: function (record, options) {
        var self = this;
        var defs = [];
        _.each(record.getFieldNames(), function (name) {
            var field = record.fields[name];
            var fieldInfo = record.fieldsInfo[record.viewType][name] || {};
            var options = fieldInfo.options || {};
            if (options.always_reload) {
                if (record.fields[name].type === 'many2one' && record.data[name]) {
                    var element = self.localData[record.data[name]];
                    defs.push(self._rpc({
                            model: field.relation,
                            method: 'name_get',
                            args: [element.data.id],
                            context: self._getContext(record, {fieldName: name}),
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
     * For a grouped list resource, this method fetches all group data by
     * performing a /read_group. It also tries to read open subgroups if they
     * were open before.
     *
     * @param {Object} list valid resource object
     * @returns {Deferred<Object>} resolves to the fetched group object
     */
    _readGroup: function (list) {
        var self = this;
        var fields = _.uniq(list.getFieldNames().concat(list.groupedBy));
        return this._rpc({
                model: list.model,
                method: 'read_group',
                fields: fields,
                domain: list.domain,
                context: list.context,
                groupBy: list.groupedBy,
                lazy: true,
            })
            .then(function (groups) {
                var rawGroupBy = list.groupedBy[0].split(':')[0];
                var previousGroups = _.map(list.data, function (groupID) {
                    return self.localData[groupID];
                });
                list.data = [];
                list.count = 0;
                var defs = [];

                _.each(groups, function (group) {
                    var aggregateValues = {};
                    _.each(group, function (value, key) {
                        if (_.contains(fields, key) && key !== list.groupedBy[0]) {
                            aggregateValues[key] = value;
                        }
                    });
                    // When a view is grouped, we need to display the name of each group in
                    // the 'title'.
                    var value = group[rawGroupBy];
                    if (list.fields[rawGroupBy].type === "selection") {
                        var choice = _.find(list.fields[rawGroupBy].selection, function (c) {
                            return c[0] === value;
                        });
                        value = choice[1];
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
                        limit: list.limit,
                        openGroupByDefault: list.openGroupByDefault,
                        type: 'list',
                        viewType: list.viewType,
                    });
                    list.data.push(newGroup.id);
                    list.count += newGroup.count;
                    var oldGroup = _.find(previousGroups, function (g) {
                        return g.res_id === newGroup.res_id && g.value === newGroup.value;
                    });
                    if (oldGroup) {
                        // restore the internal state of the group
                        _.extend(newGroup, _.pick(oldGroup, 'limit', 'isOpen', 'offset'));
                        // if the group is open and contains subgroups, also
                        // restore its data to keep internal state of sub-groups
                        if (newGroup.isOpen && newGroup.groupedBy.length) {
                            newGroup.data = oldGroup.data;
                        }
                    } else if (!newGroup.openGroupByDefault) {
                        newGroup.isOpen = false;
                    } else {
                        newGroup.isOpen = '__fold' in group ? !group.__fold : true;
                    }
                    if (newGroup.isOpen && newGroup.count > 0) {
                        defs.push(self._load(newGroup));
                    }
                });
                return $.when.apply($, defs).then(function () {
                    // generate the res_ids of the main list, being the concatenation
                    // of the fetched res_ids in each group
                    list.res_ids = _.flatten(_.map(arguments, function (group) {
                        return group ? group.res_ids : [];
                    }));
                    return list;
                });
            });
    },
    /**
     * For 'static' list, such as one2manys in a form view, we can do a /read
     * instead of a /search_read.
     *
     * @param {Object} list a valid resource object
     * @returns {Deferred -> Object} resolves to the fetched list object
     */
    _readUngroupedList: function (list) {
        var self = this;
        var def;
        var ids = [];
        var missingIds = [];
        var upper_bound = list.limit ? Math.min(list.offset + list.limit, list.count) : list.count;
        var fieldNames = list.getFieldNames();
        for (var i = list.offset; i < upper_bound; i++) {
            var id = list.res_ids[i];
            ids.push(id);
            if (!list._cache[id]) {
                missingIds.push(id);
            }
        }
        if (missingIds.length) {
            if (fieldNames.length) {
                def = this._rpc({
                    model: list.model,
                    method: 'read',
                    args: [missingIds, fieldNames],
                    context: {} // FIXME
                });
            } else {
                def = $.when(_.map(missingIds, function (id) {
                    return {id:id};
                }));
            }
        } else {
            def = $.when();
        }
        return def.then(function (records) {
            list.data = [];
            _.each(ids, function (id) {
                var dataPoint;
                if (id in list._cache) {
                    dataPoint = self.localData[list._cache[id]];
                } else {
                    dataPoint = self._makeDataPoint({
                        data: _.findWhere(records, {id: id}),
                        fieldsInfo: list.fieldsInfo,
                        fields: list.fields,
                        modelName: list.model,
                        parentID: list.id,
                        viewType: list.viewType,
                    });

                    // add many2one records
                    self._parseServerData(fieldNames, dataPoint.fields, dataPoint.data);
                    list._cache[id] = dataPoint.id;
                }
                list.data.push(dataPoint.id);
            });
            self._sortList(list);
            return list;
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
            context: list.context,
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
                    data: record,
                    fields: list.fields,
                    fieldsInfo: list.fieldsInfo,
                    modelName: list.model,
                    parentID: list.id,
                    viewType: list.viewType,
                });

                // add many2one records
                self._parseServerData(fieldNames, dataPoint.fields, dataPoint.data);
                return dataPoint.id;
            });
            if (list.loadMoreOffset) {
                list.data = list.data.concat(data);
                list.res_ids = list.res_ids.concat(ids);
            } else {
                list.data = data;
                list.res_ids = ids;
            }
            return list;
        });
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
     * that the list data has already been fetched.  Its intended use is for
     * static datasets, such as a one2many in a form view.
     *
     * @param {Object} list
     */
    _sortList: function (list) {
        var self = this;
        if (list.orderedBy.length) {
            // sort records according to ordered_by[0]
            var order = list.orderedBy[0];
            list.data.sort(function (r1, r2) {
                var data1 = self.localData[r1].data;
                var data2 = self.localData[r2].data;
                if (data1[order.name] < data2[order.name]) {
                    return order.asc ? -1 : 1;
                }
                if (data1[order.name] > data2[order.name]) {
                    return order.asc ? 1 : -1;
                }
                return 0;
            });
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
            var listData = element._changes || element.data;
            _.each(listData, function (elemId) {
                var elem = self.localData[elemId];
                self._visitChildren(elem, fn);
            });
        }
    },
});

return BasicModel;
});
