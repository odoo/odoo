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
            if (!('name' in model.fields)) {
                model.fields.name = {string: "Name", type: "char", default: "name"};
            }
            for (var fieldName in model.onchanges) {
                model.fields[fieldName].onChange = "1";
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
     * @param {string|Object} arch a string OR a parsed xml document
     * @param {string} model a model name (that should be in this.data)
     * @returns {Object} an object with 2 keys: arch and fields
     */
    fieldsViewGet: function (arch, model) {
        var fields = $.extend(true, {}, this.data[model].fields);
        var fvg = this._fieldsViewGet(arch, model, fields);
        var fields_views = {};
        fields_views[fvg.type] = fvg;
        data_manager.processViews(fields_views, fields);
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
        }
        var def;
        try {
            def = this._performRpc(route, args);
        } catch (e) {
            var error = {code: 200, data: {}, message: e.message};
            if (logLevel === 1) {
                console.warn('Mock: ' + route, error.message);
            } else if (logLevel === 2) {
                console.warn('%c[rpc] error response:', 'color: blue; font-weight: bold;', error.message);
            }
            return $.Deferred().reject(error, $.Event());
        }
        return def.then(function (result) {
            var resultString = JSON.stringify(result || false);
            if (logLevel === 1) {
                console.log('Mock: ' + route, JSON.parse(resultString));
            } else if (logLevel === 2) {
                console.log('%c[rpc] response:', 'color: blue; font-weight: bold;', JSON.parse(resultString));
            }
            return JSON.parse(resultString);
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
                record[fieldName] = model.fields[fieldName].default || false;
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
     * 'field_view_get' call to the server.
     *
     * @private
     * @param {string|Object} arch a string OR a parsed xml document
     * @param {string} model a model name (that should be in this.data)
     * @param {Object} fields
     * @returns {Object} an object with 2 keys: arch and fields (the fields
     *   appearing in the views)
     */
    _fieldsViewGet: function (arch, model, fields) {
        var self = this;
        var onchanges = this.data[model].onchanges || {};
        var fieldNodes = {};

        if (typeof arch === 'string') {
            var doc = $.parseXML(arch).documentElement;
            arch = utils.xml_to_json(doc, true);
        }

        this._traverse(arch, function (node) {
            if (typeof node === "string") {
                return false;
            }
            var modifiers = {};
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
            _.each(["invisible", "readonly", "required"], function (a) {
                if (node.attrs[a]) {
                    var v = pyeval.py_eval(node.attrs[a]);
                    if (v || modifiers[a] === undefined) {
                        modifiers[a] = v;
                    }
                }
            });
            node.attrs.modifiers = JSON.stringify(modifiers);
            if (node.tag === 'field') {
                fieldNodes[node.attrs.name] = node;
                return false;
            }
            return true;
        });

        var relModel, relFields;
        _.each(fieldNodes, function (node, name) {
            var field = fields[name];
            if (field.type === "one2many" || field.type === "many2many") {
                field.views = {};
                _.each(node.children, function (children) {
                    relModel = field.relation;
                    relFields = $.extend(true, {}, self.data[relModel].fields);
                    field.views[children.tag] = self._fieldsViewGet(children, relModel, relFields);
                });
            }

            // add onchanges
            if (name in onchanges) {
                field.onChange="1";
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
        var dom = domain[0];
        var records = this.data[model].records;
        if (dom) {
            records = _.filter(records, function (record) {
                var value = record[dom[0]];
                if (value instanceof Array) {
                    value = value[0];
                }
                if (dom[1] === 'not in') {
                    return !_.contains(dom[2], value);
                } else if (dom[1] === 'in') {
                    return _.contains(dom[2], value);
                } else if (dom[1] === '==') {
                    return dom[2] == value;
                } else if (dom[1] === '!=') {
                    return dom[2] != value;
                }
            });
        }
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
        var results = _.map(ids, function (id) {
            var record = _.findWhere(self.data[model].records, {id: id});
            if (!record) {
                throw "mock read: id does not exist...";
            }
            var result = {};
            for (var i = 0; i < fields.length; i++) {
                var field = self.data[model].fields[fields[i]];
                if (!field) {
                    // the field doens't exist on the model, so skip it
                    continue;
                }
                if (field.type === 'many2one') {
                    var relatedRecord = _.findWhere(self.data[field.relation].records, {
                        id: record[fields[i]]
                    });
                    if (relatedRecord) {
                        result[fields[i]] =
                            [record[fields[i]], relatedRecord.display_name];
                    } else {
                        result[fields[i]] = false;
                    }
                } else {
                    result[fields[i]] = record[fields[i]];
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
        var groupByField = kwargs.groupby[0];
        var result = [];

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

        var records = this._getRecords(model, kwargs.domain);
        if (groupByField) {
            var groupByFieldDescr = fields[groupByField.split(':')[0]];
            var groupByFunction, formatValue;
            if (groupByFieldDescr.type === 'date') {

                var aggregateFunction = groupByField.split(':')[1] || 'month';

                groupByField = groupByField.split(':')[0];
                groupByFunction = function (obj) {
                    if (aggregateFunction === 'day') {
                        return moment(obj[groupByField]).format('YYYY-MM-DD');
                    } else {
                        return moment(obj[groupByField]).format('MMMM YYYY');
                    }
                };
                formatValue = function (val) {
                    if (aggregateFunction === 'day') {
                        return moment(val).format('YYYY-MM-DD');
                    } else {
                        return moment(val).format('MMMM YYYY');
                    }
                };
            } else {
                groupByFunction = function (obj) {
                    return obj[groupByField];
                };
                formatValue = function (val) {
                    return val instanceof Array ? val[0] : (val || false);
                };
            }
            _.each(_.groupBy(records, groupByFunction), function (g, val) {
                val = formatValue(g[0][groupByField]);
                var group = {
                    __domain: [[
                        groupByField, "=",
                        val instanceof Array ? val[0] : (val || false)
                    ]].concat(kwargs.domain || []),
                };
                var field = self.data[model].fields[groupByField];
                if (field.type === 'many2one' && !_.isArray(val)) {
                    var related_record = _.findWhere(self.data[field.relation].records, {
                        id: val
                    });
                    if (related_record) {
                        group[groupByField] = [val, related_record.display_name];
                    } else {
                        group[groupByField] = false;
                    }
                } else {
                    group[groupByField] = val;
                }

                // compute count key to match dumb server logic...
                var countKey;
                if (kwargs.lazy) {
                    countKey = groupByField + "_count";
                } else {
                    countKey = "__count";
                }
                group[countKey] = g.length;
                aggregateFields(group, g);
                result.push($.extend(true, {}, group));
            });
        } else {
            var group = { __count: records.length };
            aggregateFields(group, records);
            result.push(group);
        }
        return result;
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
            domain: args[0],
            fields: args[1],
            offset: args[2],
            limit: args[3],
            sort: args[4],
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
        var records = this._getRecords(args.model, args.domain);
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
        if (route.indexOf('/web/image/') === 0) {
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
            return this.data[args.model][args.method](args.args, args.kwargs);
        }

        console.error("Unimplemented route", route, args);
        return $.when();
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
                // convert commands
                _.each(value, function (command) {
                    if (command[0] === 0) { // CREATE
                        var id = self._mockCreate(field.relation, command[2]);
                        record[field_changed].push(id);
                    } else if (command[0] === 1) { // UPDATE
                        self._mockWrite(field.relation, [[command[1]], command[2]]);
                    } else if (command[0] === 2) { // DELETE
                        record[field_changed] = _.without(record[field_changed], command[1]);
                    } else if (command[0] === 4) { // LINK_TO
                        // nothing to do, this command is called by a one2many,
                        // and should do nothing in a non concurrent environment.
                    } else if (command[0] === 5) { // DELETE ALL
                        record[field_changed] = [];
                    } else if (command[0] === 6) { // REPLACE WITH
                        record[field_changed] = command[2];
                    } else {
                        console.error('Command ' + JSON.stringify(command) + ' not supported by the MockServer');
                    }
                });
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
