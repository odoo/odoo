odoo.define('web.MockServer', function (require) {
"use strict";

var Class = require('web.Class');
var data_manager = require('web.data_manager');
var Domain = require('web.Domain');
var pyeval = require('web.pyeval');
var utils = require('web.utils');

var MockServer = Class.extend({
    /**
     * @constructor
     * @param {Object} data
     * @param {Object} options
     * @param {integer} [options.logLevel=0]
     * @param {string} [options.currentDate] formatted string, default to
     *   current day
     */
    init: function (data, options) {
        this.data = data;
        for (var modelName in this.data) {
            var model = this.data[modelName];
            if (!('id' in model.fields)) {
                model.fields.id = {string: "ID", type: "integer"};
            }
            if (!('display_name' in model.fields)) {
                model.fields.display_name = {string: "Display Name", type: "char"};
            }
            if (!('__last_update' in model.fields)) {
                model.fields.__last_update = {string: "Last Modified on", type: "datetime"};
            }
            if (!('name' in model.fields)) {
                model.fields.name = {string: "Name", type: "char", default: "name"};
            }
            model.records = model.records || [];

            for (var i = 0; i < model.records.length; i++) {
                var record = model.records[i];
                this._applyDefaults(model, record);
            }
        }

        // 0 is for no log
        // 1 is for short
        // 2 is for detailed
        this.logLevel = (options && options.logLevel) || 0;

        this.currentDate = options.currentDate || moment().format("YYYY-MM-DD");
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * helper: read a string describing an arch, and returns a simulated
     * 'field_view_get' call to the server. Calls processViews() of data_manager
     * to mimick the real behavior of a call to loadViews().
     *
     * @param {Object} params
     * @param {string|Object} params.arch a string OR a parsed xml document
     * @param {string} params.model a model name (that should be in this.data)
     * @param {Object} params.toolbar the actions possible in the toolbar
     * @param {Object} [params.viewOptions] the view options set in the test (optional)
     * @returns {Object} an object with 2 keys: arch and fields
     */
    fieldsViewGet: function (params) {
        var model = params.model;
        var toolbar = params.toolbar;
        var viewOptions = params.viewOptions || {};
        if (!(model in this.data)) {
            throw new Error('Model ' + model + ' was not defined in mock server data');
        }
        var fields = $.extend(true, {}, this.data[model].fields);
        var fvg = this._fieldsViewGet(params.arch, model, fields, viewOptions.context);
        var fields_views = {};
        fields_views[fvg.type] = fvg;
        data_manager.processViews(fields_views, fields);
        if (toolbar) {
            fvg.toolbar = toolbar;
        }
        return fields_views[fvg.type];
    },
    /**
     * Simulate a complete RPC call. This is the main method for this class.
     *
     * This method also log incoming and outgoing data, and stringify/parse data
     * to simulate a barrier between the server and the client. It also simulate
     * server errors.
     *
     * @param {string} route
     * @param {Object} args
     * @returns {Deferred<any>}
     *          Resolved with the result of the RPC, stringified then parsed.
     *          If the RPC should fail, the deferred will be rejected with the
     *          error object, stringified then parsed.
     */
    performRpc: function (route, args) {
        var logLevel = this.logLevel;
        args = JSON.parse(JSON.stringify(args));
        if (logLevel === 2) {
            console.log('%c[rpc] request ' + route, 'color: blue; font-weight: bold;', args);
            args = JSON.parse(JSON.stringify(args));
        }
        return this._performRpc(route, args).then(function (result) {
            var resultString = JSON.stringify(result || false);
            if (logLevel === 1) {
                console.log('Mock: ' + route, JSON.parse(resultString));
            } else if (logLevel === 2) {
                console.log('%c[rpc] response' + route, 'color: blue; font-weight: bold;', JSON.parse(resultString));
            }
            return JSON.parse(resultString);
        }).fail(function (result) {
            var errorString = JSON.stringify(result || false);
            if (logLevel === 1) {
                console.log('Mock: (ERROR)' + route, JSON.parse(errorString));
            } else if (logLevel === 2) {
                console.log('%c[rpc] response (error) ' + route, 'color: orange; font-weight: bold;', JSON.parse(errorString));
            }
            return JSON.parse(errorString);
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Apply the default values when creating an object in the local database.
     *
     * @private
     * @param {Object} model a model object from the local database
     * @param {Object} record
     */
    _applyDefaults: function (model, record) {
        record.display_name = record.display_name || record.name;
        for (var fieldName in model.fields) {
            if (fieldName === 'id') {
                continue;
            }
            if (!(fieldName in record)) {
                if ('default' in model.fields[fieldName]) {
                    record[fieldName] = model.fields[fieldName].default;
                } else if (_.contains(['one2many', 'many2many'], model.fields[fieldName].type)) {
                    record[fieldName] = [];
                } else {
                    record[fieldName] = false;
                }
            }
        }
    },
    /**
     * helper to evaluate a domain for given field values.
     * Currently, this is only a wrapper of the Domain.compute function in
     * "web.Domain".
     *
     * @param {Array} domain
     * @param {Object} fieldValues
     * @returns {boolean}
     */
    _evaluateDomain: function (domain, fieldValues) {
        return new Domain(domain).compute(fieldValues);
    },
    /**
     * helper: read a string describing an arch, and returns a simulated
     * 'fields_view_get' call to the server.
     *
     * @private
     * @param {string|Object} arch a string OR a parsed xml document
     * @param {string} model a model name (that should be in this.data)
     * @param {Object} fields
     * @param {Object} context
     * @returns {Object} an object with 2 keys: arch and fields (the fields
     *   appearing in the views)
     */
    _fieldsViewGet: function (arch, model, fields, context) {
        var self = this;
        var modifiersNames = ['invisible', 'readonly', 'required'];
        var onchanges = this.data[model].onchanges || {};
        var fieldNodes = {};

        if (typeof arch === 'string') {
            var doc = $.parseXML(arch).documentElement;
            arch = utils.xml_to_json(doc, true);
        }

        var inTreeView = (arch.tag === 'tree');

        this._traverse(arch, function (node) {
            if (typeof node === "string") {
                return false;
            }
            var modifiers = {};

            var isField = (node.tag === 'field');

            if (isField) {
                fieldNodes[node.attrs.name] = node;

                // 'transfer_field_to_modifiers' simulation
                var field = fields[node.attrs.name];

                if (!field) {
                    throw new Error("Field " + node.attrs.name + " does not exist");
                }
                var defaultValues = {};
                var stateExceptions = {};
                _.each(modifiersNames, function (attr) {
                    stateExceptions[attr] = [];
                    defaultValues[attr] = !!field[attr];
                });
                _.each(field['states'] || {}, function (modifs, state) {
                    _.each(modifs, function (modif) {
                        if (defaultValues[modif[0]] !== modif[1]) {
                            stateExceptions[modif[0]].append(state);
                        }
                    });
                });
                _.each(defaultValues, function (defaultValue, attr) {
                    if (stateExceptions[attr].length) {
                        modifiers[attr] = [("state", defaultValue ? "not in" : "in", stateExceptions[attr])];
                    } else {
                        modifiers[attr] = defaultValue;
                    }
                });
            }

            // 'transfer_node_to_modifiers' simulation
            if (node.attrs.attrs) {
                var attrs = pyeval.py_eval(node.attrs.attrs);
                _.extend(modifiers, attrs);
                delete node.attrs.attrs;
            }
            if (node.attrs.states) {
                if (!modifiers.invisible) {
                    modifiers.invisible = [];
                }
                modifiers.invisible.push(["state", "not in", node.attrs.states.split(",")]);
            }
            _.each(modifiersNames, function (a) {
                if (node.attrs[a]) {
                    var pyevalContext = window.py.dict.fromJSON(context || {});
                    var v = pyeval.py_eval(node.attrs[a], {context: pyevalContext}) ? true: false;
                    if (inTreeView && a === 'invisible') {
                        modifiers['column_invisible'] = v;
                    } else if (v || !(a in modifiers) || !_.isArray(modifiers[a])) {
                        modifiers[a] = v;
                    }
                }
            });

            // 'transfer_modifiers_to_node' simulation
            _.each(modifiersNames, function (a) {
                if (a in modifiers && (!!modifiers[a] === false || (_.isArray(modifiers[a]) && !modifiers[a].length))) {
                    delete modifiers[a];
                }
            });
            node.attrs.modifiers = JSON.stringify(modifiers);

            return !isField;
        });

        var relModel, relFields;
        _.each(fieldNodes, function (node, name) {
            var field = fields[name];
            if (field.type === "many2one" || field.type === "many2many") {
                node.attrs.can_create = node.attrs.can_create || "true";
                node.attrs.can_write = node.attrs.can_write || "true";
            }
            if (field.type === "one2many" || field.type === "many2many") {
                field.views = {};
                _.each(node.children, function (children) {
                    relModel = field.relation;
                    relFields = $.extend(true, {}, self.data[relModel].fields);
                    field.views[children.tag] = self._fieldsViewGet(children, relModel,
                        relFields, context);
                });
            }

            // add onchanges
            if (name in onchanges) {
                node.attrs.on_change="1";
            }
        });
        return {
            arch: arch,
            fields: _.pick(fields, _.keys(fieldNodes)),
            model: model,
            type: arch.tag === 'tree' ? 'list' : arch.tag,
        };
    },
    /**
     * Get all records from a model matching a domain.  The only difficulty is
     * that if we have an 'active' field, we implicitely add active = true in
     * the domain.
     *
     * @private
     * @param {string} model a model name
     * @param {any[]} domain
     * @returns {Object[]} a list of records
     */
    _getRecords: function (model, domain) {
        if (!_.isArray(domain)) {
            throw new Error("MockServer._getRecords: given domain has to be an array.");
        }

        var self = this;
        var records = this.data[model].records;

        if ('active' in this.data[model].fields) {
            // add ['active', '=', true] to the domain if 'active' is not yet present in domain
            var activeInDomain = false;
            _.each(domain, function (subdomain) {
                activeInDomain = activeInDomain || subdomain[0] === 'active';
            });
            if (!activeInDomain) {
                domain.unshift(['active', '=', true]);
            }
        }

        if (domain.length) {
            records = _.filter(records, function (record) {
                var fieldValues = _.mapObject(record, function (value) {
                    return value instanceof Array ? value[0] : value;
                });
                return self._evaluateDomain(domain, fieldValues);
            });
        }

        return records;
    },
    /**
     * Helper function, to find an available ID. The current algorithm is to add
     * all other IDS.
     *
     * @private
     * @param {string} modelName
     * @returns {integer} a valid ID (> 0)
     */
    _getUnusedID: function (modelName) {
        var model = this.data[modelName];
        return _.reduce(model.records, function (acc, record){
            return acc + record.id;
        }, 1);
    },
    /**
     * Simulate a 'copy' operation, so we simply try to duplicate a record in
     * memory
     *
     * @private
     * @param {string} modelName
     * @param {integer} id the ID of a valid record
     * @returns {integer} the ID of the duplicated record
     */
    _mockCopy: function (modelName, id) {
        var model = this.data[modelName];
        var newID = this._getUnusedID(modelName);
        var originalRecord = _.findWhere(model.records, {id: id});
        var duplicateRecord = _.extend({}, originalRecord, {id: newID});
        duplicateRecord.display_name = originalRecord.display_name + ' (copy)';
        model.records.push(duplicateRecord);
        return newID;
    },
    /**
     * Simulate a 'create' operation.  This is basically a 'write' with the
     * added work of getting a valid ID and applying default values.
     *
     * @private
     * @param {string} modelName
     * @param {Object} values
     * @returns {integer}
     */
    _mockCreate: function (modelName, values) {
        if ('id' in values) {
            throw "Cannot create a record with a predefinite id";
        }
        var model = this.data[modelName];
        var id = this._getUnusedID(modelName);
        var record = {id: id};
        model.records.push(record);
        this._applyDefaults(model, values);
        this._mockWrite(modelName, [[id], values]);
        return id;
    },
    /**
     * Simulate a 'default_get' operation
     *
     * @private
     * @param {string} modelName
     * @param {array[]} args a list with a list of fields in the first position
     * @param {Object} [kwargs]
     * @param {Object} [kwargs.context] the context to eventually read default
     *   values
     * @returns {Object}
     */
    _mockDefaultGet: function (modelName, args, kwargs) {
        var result = {};
        var fields = args[0];
        var model = this.data[modelName];
        _.each(fields, function (name) {
            var field = model.fields[name];
            if ('default' in field) {
                result[name] = field.default;
            }
        });
        if (kwargs && kwargs.context)
        _.each(kwargs.context, function (value, key) {
            if ('default_' === key.slice(0, 8)) {
                result[key.slice(8)] = value;
            }
        });
        return result;
    },
    /**
     * Simulate a 'field_get' operation
     *
     * @private
     * @param {string} modelName
     * @param {any} args
     * @returns {Object}
     */
    _mockFieldsGet: function (modelName, args) {
        var modelFields = this.data[modelName].fields;
        // Get only the asked fields (args[0] could be the field names)
        if (args[0] && args[0].length) {
            modelFields = _.pick.apply(_, [modelFields].concat(args[0]));
        }
        // Get only the asked attributes (args[1] could be the attribute names)
        if (args[1] && args[1].length) {
            modelFields = _.mapObject(modelFields, function (field) {
                return _.pick.apply(_, [field].concat(args[1]));
            });
        }
        return modelFields;
    },
    /**
     * Simulate a 'name_get' operation
     *
     * @private
     * @param {string} model
     * @param {Array} args
     * @returns {Array[]} a list of [id, display_name]
     */
    _mockNameGet: function (model, args) {
        var ids = args[0];
        if (!_.isArray(ids)) {
            ids = [ids];
        }
        var records = this.data[model].records;
        var names = _.map(ids, function (id) {
            return [id, _.findWhere(records, {id: id}).display_name];
        });
        return names;
    },
    /**
     * Simulate a 'name_create' operation
     *
     * @private
     * @param {string} model
     * @param {Array} args
     * @returns {Array} a couple [id, name]
     */
    _mockNameCreate: function (model, args) {
        var name = args[0];
        var values = {
            name: name,
            display_name: name,
        };
        var id = this._mockCreate(model, values);
        return [id, name];
    },
    /**
     * Simulate a 'name_search' operation.
     *
     * not yet fully implemented (missing: limit, and evaluate operators)
     * domain works but only to filter on ids
     *
     * @private
     * @param {string} model
     * @param {Array} args
     * @param {string} args[0]
     * @param {Array} args[1], search domain
     * @param {Object} _kwargs
     * @returns {Array[]} a list of [id, display_name]
     */
    _mockNameSearch: function (model, args, _kwargs) {
        var str = args && typeof args[0] === 'string' ? args[0] : _kwargs.name;
        var domain = (args && args[1]) || _kwargs.args || [];
        var records = this._getRecords(model, domain);
        if (str.length) {
            records = _.filter(records, function (record) {
                return record.display_name.indexOf(str) !== -1;
            });
        }
        return _.map(records, function (record) {
            return [record.id, record.display_name];
        });
    },
    /**
     * Simulate an 'onchange' rpc
     *
     * @private
     * @param {string} model
     * @param {string|string[]} args a list of field names, or just a field name
     * @returns {Object}
     */
    _mockOnchange: function (model, args) {
        var onchanges = this.data[model].onchanges || {};
        var record = args[1];
        var fields = args[2];
        if (!(fields instanceof Array)) {
            fields = [fields];
        }
        var result = {};
        _.each(fields, function (field) {
            if (field in onchanges) {
                var changes = _.clone(record);
                onchanges[field](changes);
                _.each(changes, function (value, key) {
                    if (record[key] !== value) {
                        result[key] = value;
                    }
                });
            }
        });
        return {value: result};
    },
    /**
     * Simulate a 'read' operation.
     *
     * @private
     * @param {string} model
     * @param {Array} args
     * @param {Object} _kwargs ignored... is that correct?
     * @returns {Object}
     */
    _mockRead: function (model, args, _kwargs) {
        var self = this;
        var ids = args[0];
        if (!_.isArray(ids)) {
            ids = [ids];
        }
        var fields = args[1] && args[1].length ? _.uniq(args[1].concat(['id'])) : Object.keys(this.data[model].fields);
        var records = _.reduce(ids, function (records, id) {
            if (!id) {
                throw "mock read: falsy value given as id, would result in an access error in actual server !";
            }
            var record =  _.findWhere(self.data[model].records, {id: id});
            return record ? records.concat(record) : records;
        }, []);
        var results = _.map(records, function (record) {
            var result = {};
            for (var i = 0; i < fields.length; i++) {
                var field = self.data[model].fields[fields[i]];
                if (!field) {
                    // the field doens't exist on the model, so skip it
                    continue;
                }
                if (field.type === 'float' ||
                    field.type === 'integer' ||
                    field.type === 'monetary') {
                    // read should return 0 for unset numeric fields
                    result[fields[i]] = record[fields[i]] || 0;
                } else if (field.type === 'many2one') {
                    var relatedRecord = _.findWhere(self.data[field.relation].records, {
                        id: record[fields[i]]
                    });
                    if (relatedRecord) {
                        result[fields[i]] =
                            [record[fields[i]], relatedRecord.display_name];
                    } else {
                        result[fields[i]] = false;
                    }
                } else if (field.type === 'one2many' || field.type === 'many2many') {
                    result[fields[i]] = record[fields[i]] || [];
                } else {
                    result[fields[i]] = record[fields[i]] || false;
                }
            }
            return result;
        });
        return results;
    },
    /**
     * Simulate a 'read_group' call to the server.
     *
     * Note: most of the keys in kwargs are still ignored
     *
     * @private
     * @param {string} model a string describing an existing model
     * @param {Object} kwargs various options supported by read_group
     * @param {string[]} kwargs.groupby fields that we are grouping
     * @param {string[]} kwargs.fields fields that we are aggregating
     * @param {Array} kwargs.domain the domain used for the read_group
     * @param {boolean} kwargs.lazy still mostly ignored
     * @param {integer} kwargs.limit ignored as well
     * @returns {Object[]}
     */
    _mockReadGroup: function (model, kwargs) {
        if (!('lazy' in kwargs)) {
            kwargs.lazy = true;
        }
        var self = this;
        var fields = this.data[model].fields;
        var aggregatedFields = _.clone(kwargs.fields);
        var groupBy = [];
        if (kwargs.groupby.length) {
            groupBy = kwargs.lazy ? [kwargs.groupby[0]] : kwargs.groupby;
        }
        var records = this._getRecords(model, kwargs.domain);

        // if no fields have been given, the server picks all stored fields
        if (aggregatedFields.length === 0) {
            aggregatedFields = _.keys(this.data[model].fields);
        }

        // filter out non existing fields
        aggregatedFields = _.filter(aggregatedFields, function (name) {
            return name in self.data[model].fields;
        });

        function aggregateFields(group, records) {
            var type;
            for (var i = 0; i < aggregatedFields.length; i++) {
                type = fields[aggregatedFields[i]].type;
                if (type === 'float' || type === 'integer') {
                    group[aggregatedFields[i]] = 0;
                    for (var j = 0; j < records.length; j++) {
                        group[aggregatedFields[i]] += records[j][aggregatedFields[i]];
                    }
                }
            }
        }
        function formatValue(groupByField, val) {
            var fieldName = groupByField.split(':')[0];
            var aggregateFunction = groupByField.split(':')[1] || 'month';
            if (fields[fieldName].type === 'date') {
                if (!val) {
                    return false;
                } else if (aggregateFunction === 'day') {
                    return moment(val).format('YYYY-MM-DD');
                } else {
                    return moment(val).format('MMMM YYYY');
                }
            } else {
                return val instanceof Array ? val[0] : (val || false);
            }
        }
        function groupByFunction(record) {
            var value = '';
            _.each(groupBy, function (groupByField) {
                value = (value ? value + ',' : value) + groupByField + '#';
                var fieldName = groupByField.split(':')[0];
                if (fields[fieldName].type === 'date') {
                    var aggregateFunction = groupByField.split(':')[1] || 'month';
                    if (aggregateFunction === 'day') {
                        value += moment(record[fieldName]).format('YYYY-MM-DD');
                    } else {
                        value += moment(record[fieldName]).format('MMMM YYYY');
                    }
                } else {
                    value += record[groupByField];
                }
            });
            return value;
        }

        if (!groupBy.length) {
            var group = { __count: records.length };
            aggregateFields(group, records);
            return [group];
        }

        var groups = _.groupBy(records, groupByFunction);
        var result = _.map(groups, function (group) {
            var res = {
                __domain: kwargs.domain || [],
            };
            _.each(groupBy, function (groupByField) {
                var fieldName = groupByField.split(':')[0];
                var val = formatValue(groupByField, group[0][fieldName]);
                var field = self.data[model].fields[fieldName];
                if (field.type === 'many2one' && !_.isArray(val)) {
                    var related_record = _.findWhere(self.data[field.relation].records, {
                        id: val
                    });
                    if (related_record) {
                        res[groupByField] = [val, related_record.display_name];
                    } else {
                        res[groupByField] = false;
                    }
                } else {
                    res[groupByField] = val;
                }
                res.__domain = [[fieldName, "=", val]].concat(res.__domain);
            });

            // compute count key to match dumb server logic...
            var countKey;
            if (kwargs.lazy) {
                countKey = groupBy[0].split(':')[0] + "_count";
            } else {
                countKey = "__count";
            }
            res[countKey] = group.length;
            aggregateFields(res, group);

            return res;
        });

        if (kwargs.orderby) {
            // only consider first sorting level
            kwargs.orderby = kwargs.orderby.split(',')[0];
            var fieldName = kwargs.orderby.split(' ')[0];
            var order = kwargs.orderby.split(' ')[1];
            result.sort(function (g1, g2) {
                if (g1[fieldName] < g2[fieldName]) {
                    return order === 'ASC' ? -1 : 1;
                }
                if (g1[fieldName] > g2[fieldName]) {
                    return order === 'ASC' ? 1 : -1;
                }
                return 0;
            });
        }

        return result;
    },
    /**
     * Simulates a 'read_progress_bar' operation
     *
     * @private
     * @param {string} model
     * @param {Object} kwargs
     * @returns {Object[][]}
     */
    _mockReadProgressBar: function (model, kwargs) {
        var domain = kwargs.domain;
        var groupBy = kwargs.groupBy;
        var progress_bar = kwargs.progress_bar;

        var records = this._getRecords(model, domain || []);

        var data = {};
        _.each(records, function (record) {
            var groupByValue = record[groupBy]; // always technical value here

            if (!(groupByValue in data)) {
                data[groupByValue] = {};
                _.each(progress_bar.colors, function (val, key) {
                    data[groupByValue][key] = 0;
                });
            }

            var fieldValue = record[progress_bar.field];
            if (fieldValue in data[groupByValue]) {
                data[groupByValue][fieldValue]++;
            }
        });

        return data;
    },
    /**
     * Simulate a 'search_count' operation
     *
     * @private
     * @param {string} model
     * @param {Array} args
     * @returns {integer}
     */
    _mockSearchCount: function (model, args) {
        return this._getRecords(model, args[0]).length;
    },
    /**
     * Simulate a 'search_read' operation on a model
     *
     * @private
     * @param {Object} args
     * @param {Array} args.domain
     * @param {string} args.model
     * @param {Array} [args.fields] defaults to the list of all fields
     * @param {integer} [args.limit]
     * @param {integer} [args.offset=0]
     * @param {string[]} [args.sort]
     * @returns {Object}
     */
    _mockSearchRead: function (model, args, kwargs) {
        var result = this._mockSearchReadController({
            model: model,
            domain: kwargs.domain || args[0],
            fields: kwargs.fields || args[1],
            offset: kwargs.offset || args[2],
            limit: kwargs.limit || args[3],
            order: kwargs.order || args[4],
            context: kwargs.context,
        });
        return result.records;
    },
    /**
     * Simulate a 'search_read' operation, from the controller point of view
     *
     * @private
     * @private
     * @param {Object} args
     * @param {Array} args.domain
     * @param {string} args.model
     * @param {Array} [args.fields] defaults to the list of all fields
     * @param {integer} [args.limit]
     * @param {integer} [args.offset=0]
     * @param {string[]} [args.sort]
     * @returns {Object}
     */
    _mockSearchReadController: function (args) {
        var self = this;
        var records = this._getRecords(args.model, args.domain || []);
        var fields = args.fields || _.keys(this.data[args.model].fields);
        var nbRecords = records.length;
        var offset = args.offset || 0;
        records = records.slice(offset, args.limit ? (offset + args.limit) : nbRecords);
        var processedRecords = _.map(records, function (r) {
            var result = {};
            _.each(_.uniq(fields.concat(['id'])), function (fieldName) {
                var field = self.data[args.model].fields[fieldName];
                if (field.type === 'many2one') {
                    var related_record = _.findWhere(self.data[field.relation].records, {
                        id: r[fieldName]
                    });
                    result[fieldName] =
                        related_record ? [r[fieldName], related_record.display_name] : false;
                } else {
                    result[fieldName] = r[fieldName];
                }
            });
            return result;
        });
        if (args.sort) {
            // deal with sort on multiple fields (i.e. only consider the first)
            args.sort = args.sort.split(',')[0];
            var fieldName = args.sort.split(' ')[0];
            var order = args.sort.split(' ')[1];
            processedRecords.sort(function (r1, r2) {
                if (r1[fieldName] < r2[fieldName]) {
                    return order === 'ASC' ? -1 : 1;
                }
                if (r1[fieldName] > r2[fieldName]) {
                    return order === 'ASC' ? 1 : -1;
                }
                return 0;
            });
        }
        var result = {
            length: nbRecords,
            records: processedRecords,
        };
        return $.extend(true, {}, result);
    },
    /**
     * Simulate a 'unlink' operation
     *
     * @private
     * @param {string} model
     * @param {Array} args
     * @returns {boolean} currently, always returns true
     */
    _mockUnlink: function (model, args) {
        var ids = args[0];
        if (!_.isArray(ids)) {
            ids = [ids];
        }
        this.data[model].records = _.reject(this.data[model].records, function (record) {
            return _.contains(ids, record.id);
        });

        // update value of one2many fields pointing to the deleted records
        _.each(this.data, function (d) {
            var relatedFields = _.pick(d.fields, function (field) {
                return field.type === 'one2many' && field.relation === model;
            });
            _.each(Object.keys(relatedFields), function (relatedField) {
                _.each(d.records, function (record) {
                    record[relatedField] = _.difference(record[relatedField], ids);
                });
            });
        });

        return true;
    },
    /**
     * Simulate a 'write' operation
     *
     * @private
     * @param {string} model
     * @param {Array} args
     * @returns {boolean} currently, always return 'true'
     */
    _mockWrite: function (model, args) {
        _.each(args[0], this._writeRecord.bind(this, model, args[1]));
        return true;
    },
    /**
     * Dispatch a RPC call to the correct helper function
     *
     * @see performRpc
     *
     * @private
     * @param {string} route
     * @param {Object} args
     * @returns {Deferred<any>}
     *          Resolved with the result of the RPC. If the RPC should fail, the
     *          deferred should either be rejected or the call should throw an
     *          exception (@see performRpc for error handling).
     */
    _performRpc: function (route, args) {
        switch (route) {
            case '/web/action/load':
                return $.when(this._mockLoadAction(args));

            case '/web/dataset/search_read':
                return $.when(this._mockSearchReadController(args));
        }
        if (route.indexOf('/web/image') >= 0 || _.contains(['.png', '.jpg'], route.substr(route.length - 4))) {
            return $.when();
        }
        switch (args.method) {
            case 'copy':
                return $.when(this._mockCopy(args.model, args.args[0]));

            case 'create':
                return $.when(this._mockCreate(args.model, args.args[0]));

            case 'default_get':
                return $.when(this._mockDefaultGet(args.model, args.args, args.kwargs));

            case 'fields_get':
                return $.when(this._mockFieldsGet(args.model, args.args));

            case 'name_get':
                return $.when(this._mockNameGet(args.model, args.args));

            case 'name_create':
                return $.when(this._mockNameCreate(args.model, args.args));

            case 'name_search':
                return $.when(this._mockNameSearch(args.model, args.args, args.kwargs));

            case 'onchange':
                return $.when(this._mockOnchange(args.model, args.args));

            case 'read':
                return $.when(this._mockRead(args.model, args.args, args.kwargs));

            case 'read_group':
                return $.when(this._mockReadGroup(args.model, args.kwargs));

            case 'read_progress_bar':
                return $.when(this._mockReadProgressBar(args.model, args.kwargs));

            case 'search_count':
                return $.when(this._mockSearchCount(args.model, args.args));

            case 'search_read':
                return $.when(this._mockSearchRead(args.model, args.args, args.kwargs));

            case 'unlink':
                return $.when(this._mockUnlink(args.model, args.args));

            case 'write':
                return $.when(this._mockWrite(args.model, args.args));
        }
        var model = this.data[args.model];
        if (model && typeof model[args.method] === 'function') {
            return $.when(this.data[args.model][args.method](args.args, args.kwargs));
        }

        throw new Error("Unimplemented route: " + route);
    },
    /**
     * helper function: traverse a tree and apply the function f to each of its
     * nodes.
     *
     * Note: this should be abstracted somewhere in web.utils, or in
     * web.tree_utils
     *
     * @param {Object} tree object with a 'children' key, which contains an
     *   array of trees.
     * @param {function} f
     */
    _traverse: function (tree, f) {
        var self = this;
        if (f(tree)) {
            _.each(tree.children, function (c) { self._traverse(c, f); });
        }
    },
    /**
     * Write a record. The main difficulty is that we have to apply x2many
     * commands
     *
     * @private
     * @param {string} model
     * @param {Object} values
     * @param {integer} id
     */
    _writeRecord: function (model, values, id) {
        var self = this;
        var record = _.findWhere(this.data[model].records, {id: id});
        for (var field_changed in values) {
            var field = this.data[model].fields[field_changed];
            var value = values[field_changed];
            if (!field) {
                console.warn("Mock: Can't write on field '" + field_changed + "' on model '" + model + "' (field is undefined)");
                continue;
            }
            if (_.contains(['one2many', 'many2many'], field.type)) {
                var ids = _.clone(record[field_changed]) || [];
                // convert commands
                _.each(value, function (command) {
                    if (command[0] === 0) { // CREATE
                        var id = self._mockCreate(field.relation, command[2]);
                        ids.push(id);
                    } else if (command[0] === 1) { // UPDATE
                        self._mockWrite(field.relation, [[command[1]], command[2]]);
                    } else if (command[0] === 2) { // DELETE
                        ids = _.without(ids, command[1]);
                    } else if (command[0] === 3) { // FORGET
                        ids = _.without(ids, command[1]);
                    } else if (command[0] === 4) { // LINK_TO
                        if (!_.contains(ids, command[1])) {
                            ids.push(command[1]);
                        }
                    } else if (command[0] === 5) { // DELETE ALL
                        ids = [];
                    } else if (command[0] === 6) { // REPLACE WITH
                        ids = command[2];
                    } else {
                        console.error('Command ' + JSON.stringify(command) + ' not supported by the MockServer');
                    }
                });
                record[field_changed] = ids;
            } else if (field.type === 'many2one') {
                if (value) {
                    var relatedRecord = _.findWhere(this.data[field.relation].records, {
                        id: value
                    });
                    if (!relatedRecord) {
                        throw "Wrong id for a many2one";
                    } else {
                        record[field_changed] = value;
                    }
                } else {
                    record[field_changed] = false;
                }
            } else {
                record[field_changed] = value;
            }
        }
    },
});

return MockServer;

});
