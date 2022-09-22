odoo.define('web.MockServer', function (require) {
"use strict";

var Class = require('web.Class');
var Domain = require('web.Domain');
var pyUtils = require('web.py_utils');

var MockServer = Class.extend({
    /**
     * @constructor
     * @param {Object} data
     * @param {Object} options
     * @param {Object[]} [options.actions=[]]
     * @param {Object} [options.archs={}] dict of archs with keys being strings like
     *    'model,id,viewType'
     * @param {boolean} [options.debug=false] logs RPCs if set to true
     * @param {string} [options.currentDate] formatted string, default to
     *   current day
     */
    init: function (data, options) {
        options = options || {};
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

        this.debug = options.debug;

        this.currentDate = options.currentDate || moment().format("YYYY-MM-DD");

        this.actions = options.actions || [];
        this.archs = options.archs || {};
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Mocks a fields_get RPC for a given model.
     *
     * @param {string} model
     * @returns {Object}
     */
    fieldsGet: function (model) {
        return this.data[model].fields;
    },
    /**
     * helper: read a string describing an arch, and returns a simulated
     * 'field_view_get' call to the server. Calls processViews() of data_manager
     * to mimick the real behavior of a call to loadViews().
     *
     * @param {Object} params
     * @param {string|Object} params.arch a string OR a parsed xml document
     * @param {Number} [params.view_id] the id of the arch's view
     * @param {string} params.model a model name (that should be in this.data)
     * @param {Object} params.toolbar the actions possible in the toolbar
     * @param {Object} [params.viewOptions] the view options set in the test (optional)
     * @returns {Object} an object with 2 keys: arch and fields
     */
    fieldsViewGet: function (params) {
        var model = params.model;
        var toolbar = params.toolbar;
        var viewId = params.view_id;
        var viewOptions = params.viewOptions || {};
        if (!(model in this.data)) {
            throw new Error('Model ' + model + ' was not defined in mock server data');
        }
        var fields = $.extend(true, {}, this.data[model].fields);
        var fvg = this._fieldsViewGet(params.arch, model, fields, viewOptions.context || {});
        if (toolbar) {
            fvg.toolbar = toolbar;
        }
        if (viewId) {
            fvg.view_id = viewId;
        }
        return fvg;
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
     * @returns {Promise<any>}
     *          Resolved with the result of the RPC, stringified then parsed.
     *          If the RPC should fail, the promise will be rejected with the
     *          error object, stringified then parsed.
     */
    performRpc: function (route, args) {
        var debug = this.debug;
        args = JSON.parse(JSON.stringify(args));
        if (debug) {
            console.log('%c[rpc] request ' + route, 'color: blue; font-weight: bold;', args);
            args = JSON.parse(JSON.stringify(args));
        }
        var def = this._performRpc(route, args);

        var abort = def.abort || def.reject;
        if (abort) {
            abort = abort.bind(def);
        } else {
            abort = function () {
                throw new Error("Can't abort this request");
            };
        }

        def = def.then(function (result) {
            var resultString = JSON.stringify(result || false);
            if (debug) {
                console.log('%c[rpc] response' + route, 'color: blue; font-weight: bold;', JSON.parse(resultString));
            }
            return JSON.parse(resultString);
        }, function (result) {
            var message = result && result.message;
            var event = result && result.event;
            var errorString = JSON.stringify(message || false);
            if (debug) {
                console.log('%c[rpc] response (error) ' + route, 'color: orange; font-weight: bold;', JSON.parse(errorString));
            }
            return Promise.reject({message: errorString, event: event || $.Event()});
        });

        def.abort = abort;
        return def;
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
     * @param {string} arch a string OR a parsed xml document
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
        var groupbyNodes = {};

        var doc;
        if (typeof arch === 'string') {
            doc = $.parseXML(arch).documentElement;
        } else {
            doc = arch;
        }

        var inTreeView = (doc.tagName === 'tree');

        // mock _postprocess_access_rights
        const isBaseModel = !context.base_model_name || (model === context.base_model_name);
        var views = ['kanban', 'tree', 'form', 'gantt', 'activity'];
        if (isBaseModel && views.indexOf(doc.tagName) !== -1) {
            for (let action of ['create', 'delete', 'edit', 'write']) {
                if (!doc.getAttribute(action) && action in context && !context[action]) {
                    doc.setAttribute(action, 'false');
                }
            }
        }

        this._traverse(doc, function (node) {
            if (node.nodeType === Node.TEXT_NODE) {
                return false;
            }
            var modifiers = {};

            var isField = (node.tagName === 'field');
            var isGroupby = (node.tagName === 'groupby');

            if (isField) {
                var fieldName = node.getAttribute('name');
                fieldNodes[fieldName] = node;

                // 'transfer_field_to_modifiers' simulation
                var field = fields[fieldName];

                if (!field) {
                    throw new Error("Field " + fieldName + " does not exist");
                }
                var defaultValues = {};
                var stateExceptions = {};
                _.each(modifiersNames, function (attr) {
                    stateExceptions[attr] = [];
                    defaultValues[attr] = !!field[attr];
                });
                _.each(field.states || {}, function (modifs, state) {
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
            } else if (isGroupby && !node._isProcessed) {
                var groupbyName = node.getAttribute('name');
                fieldNodes[groupbyName] = node;
                groupbyNodes[groupbyName] = node;
            }

            // 'transfer_node_to_modifiers' simulation
            var attrs = node.getAttribute('attrs');
            if (attrs) {
                attrs = pyUtils.py_eval(attrs);
                _.extend(modifiers, attrs);
            }

            var states = node.getAttribute('states');
            if (states) {
                if (!modifiers.invisible) {
                    modifiers.invisible = [];
                }
                modifiers.invisible.push(["state", "not in", states.split(",")]);
            }
            _.each(modifiersNames, function (a) {
                var mod = node.getAttribute(a);
                if (mod) {
                    var pyevalContext = window.py.dict.fromJSON(context || {});
                    var v = pyUtils.py_eval(mod, {context: pyevalContext}) ? true: false;
                    if (inTreeView && a === 'invisible') {
                        modifiers.column_invisible = v;
                    } else if (v || !(a in modifiers) || !_.isArray(modifiers[a])) {
                        modifiers[a] = v;
                    }
                }
            });

            _.each(modifiersNames, function (a) {
                if (a in modifiers && (!!modifiers[a] === false || (_.isArray(modifiers[a]) && !modifiers[a].length))) {
                    delete modifiers[a];
                }
            });

            if (Object.keys(modifiers).length) {
                node.setAttribute('modifiers', JSON.stringify(modifiers));
            }

            if (isGroupby && !node._isProcessed) {
                return false;
            }

            return !isField;
        });

        var relModel, relFields;
        _.each(fieldNodes, function (node, name) {
            var field = fields[name];
            if (field.type === "many2one" || field.type === "many2many") {
                var canCreate = node.getAttribute('can_create');
                node.setAttribute('can_create', canCreate || "true");
                var canWrite = node.getAttribute('can_write');
                node.setAttribute('can_write', canWrite || "true");
            }
            if (field.type === "one2many" || field.type === "many2many") {
                field.views = {};
                _.each(node.childNodes, function (children) {
                    if (children.tagName) { // skip text nodes
                        relModel = field.relation;
                        relFields = $.extend(true, {}, self.data[relModel].fields);
                        field.views[children.tagName] = self._fieldsViewGet(children, relModel,
                            relFields, _.extend({}, context, {base_model_name: model}));
                    }
                });
            }

            // add onchanges
            if (name in onchanges) {
                node.setAttribute('on_change', "1");
            }
        });
        _.each(groupbyNodes, function (node, name) {
            var field = fields[name];
            if (field.type !== 'many2one') {
                throw new Error('groupby can only target many2one');
            }
            field.views = {};
            relModel = field.relation;
            relFields = $.extend(true, {}, self.data[relModel].fields);
            node._isProcessed = true;
            // postprocess simulation
            field.views.groupby = self._fieldsViewGet(node, relModel, relFields, context);
            while (node.firstChild) {
                node.removeChild(node.firstChild);
            }
        });

        var xmlSerializer = new XMLSerializer();
        var processedArch = xmlSerializer.serializeToString(doc);
        return {
            arch: processedArch,
            fields: _.pick(fields, _.keys(fieldNodes)),
            model: model,
            type: doc.tagName === 'tree' ? 'list' : doc.tagName,
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
                domain = [['active', '=', true]].concat(domain);
            }
        }

        if (domain.length) {
            // 'child_of' operator isn't supported by domain.js, so we replace
            // in by the 'in' operator (with the ids of children)
            domain = domain.map(function (criterion) {
                if (criterion[1] === 'child_of') {
                    var oldLength = 0;
                    var childIDs = [criterion[2]];
                    while (childIDs.length > oldLength) {
                        oldLength = childIDs.length;
                        _.each(records, function (r) {
                            if (childIDs.indexOf(r.parent_id) >= 0) {
                                childIDs.push(r.id);
                            }
                        });
                    }
                    criterion = [criterion[0], 'in', childIDs];
                }
                return criterion;
            });
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
     * Simulate a 'fields_get' operation
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
     * Simulate a call to the 'search_panel_select_range' method.
     *
     * Note that the implementation assumes that 'parent_id' is the field that
     * encodes the parent relationship.
     *
     * @private
     * @param {string} model
     * @param {Array} args
     * @returns {Object}
     */
    _mockSearchPanelSelectRange: function (model, args) {
        var fieldName = args[0];
        var field = this.data[model].fields[fieldName];

        if (field.type !== 'many2one') {
            throw new Error('Only fields of type many2one are handled');
        }

        var fields = ['display_name'];
        var parentField = this.data[field.relation].fields.parent_id;
        if (parentField) {
            fields.push('parent_id');
        }
        return {
            parent_field: parentField ? 'parent_id' : false,
            values: this._mockSearchRead(field.relation, [[], fields], {}),
        };
    },
    /**
     * Simulate a call to the 'search_panel_select_multi_range' method.
     *
     * Note that only the many2one and selection cases are handled by this
     * function.
     *
     * @param {string} model
     * @param {Array} args
     * @param {Object} kwargs
     * @returns {Object}
     */
    _mockSearchPanelSelectMultiRange: function (model, args, kwargs) {
        var fieldName = args[0];
        var field = this.data[model].fields[fieldName];
        var comodelDomain = kwargs.comodel_domain || [];

        if (!_.contains(['many2one', 'selection'], field.type)) {
            throw new Error('Only fields of type many2one and selection are handled');
        }

        var modelDomain;
        var disableCounters = kwargs.disable_counters || false;
        modelDomain = [[fieldName, '!=', false]]
                            .concat(kwargs.category_domain)
                            .concat(kwargs.filter_domain)
                            .concat(kwargs.search_domain);
        var groupBy = kwargs.group_by || false;
        var comodel = field.relation || false;
        var groupByField = groupBy && this.data[comodel].fields[groupBy];

        // get counters
        var groups;
        var counters = {};
        if (!disableCounters) {
            groups = this._mockReadGroup(model, {
                domain: modelDomain,
                fields: [fieldName],
                groupby: [fieldName],
            });
            groups.forEach(function (group) {
                var groupId = field.type === 'many2one' ? group[fieldName][0] : group[fieldName];
                counters[groupId] = group[fieldName + '_count'];
            });
        }

        // get filter values
        var filterValues = [];
        if (field.type === 'many2one') {
            var fields = groupBy ? ['display_name', groupBy] : ['display_name'];
            var records = this._mockSearchRead(comodel, [comodelDomain, fields], {});
            records.forEach(function (record) {
                var filterValue = {
                    count: counters[record.id] || 0,
                    id: record.id,
                    name: record.display_name,
                };
                if (groupBy) {
                    var id = record[groupBy];
                    var name = record[groupBy];
                    if (groupByField.type === 'many2one') {
                        name = id[1];
                        id = id[0];
                    } else if (groupByField.type === 'selection') {
                        name = _.find(field.selection, function (option) {
                            return option[0] === id;
                        })[1];
                    }
                    filterValue.group_id = id;
                    filterValue.group_name = name;
                }
                filterValues.push(filterValue);
            });
        } else if (field.type === 'selection') {
            field.selection.forEach(function (option) {
                filterValues.push({
                    count: counters[option[0]] || 0,
                    id: option[0],
                    name: option[1],
                });
            });
        }

        return filterValues;
    },
    /**
     * Simulate a call to the '/web/action/load' route
     *
     * @private
     * @param {Object} kwargs
     * @param {integer} kwargs.action_id
     * @returns {Object}
     */
    _mockLoadAction: function (kwargs) {
        var action = _.findWhere(this.actions, {id: parseInt(kwargs.action_id)});
        if (!action) {
            // when the action doesn't exist, the real server doesn't crash, it
            // simply returns false
            console.warn("No action found for ID " + kwargs.action_id);
        }
        return action || false;
    },
    /**
     * Simulate a 'load_views' operation
     *
     * @param {string} model
     * @param {Array} args
     * @param {Object} kwargs
     * @param {Array} kwargs.views
     * @param {Object} kwargs.options
     * @param {Object} kwargs.context
     * @returns {Object}
     */
    _mockLoadViews: function (model, kwargs) {
        var self = this;
        var views = {};
        _.each(kwargs.views, function (view_descr) {
            var viewID = view_descr[0] || false;
            var viewType = view_descr[1];
            if (!viewID) {
                var contextKey = (viewType === 'list' ? 'tree' : viewType) + '_view_ref';
                if (contextKey in kwargs.context) {
                    viewID = kwargs.context[contextKey];
                }
            }
            var key = [model, viewID, viewType].join(',');
            var arch = self.archs[key] || _.find(self.archs, function (_v, k) {
                var ka = k.split(',');
                viewID = parseInt(ka[1], 10);
                return ka[0] === model && ka[2] === viewType;
            });
            if (!arch) {
                throw new Error('No arch found for key ' + key);
            }
            views[viewType] = {
                arch: arch,
                view_id: viewID,
                model: model,
                viewOptions: {
                    context: kwargs.context,
                },
            };
        });
        return views;
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
     * @param {number} [_kwargs.limit=100] server-side default limit
     * @returns {Array[]} a list of [id, display_name]
     */
    _mockNameSearch: function (model, args, _kwargs) {
        var str = args && typeof args[0] === 'string' ? args[0] : _kwargs.name;
        const limit = _kwargs.limit || 100;
        var domain = (args && args[1]) || _kwargs.args || [];
        var records = this._getRecords(model, domain);
        if (str.length) {
            records = _.filter(records, function (record) {
                return record.display_name.indexOf(str) !== -1;
            });
        }
        var result = _.map(records, function (record) {
            return [record.id, record.display_name];
        });
        return result.slice(0, limit);
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
     * @param {integer} [kwargs.limit]
     * @param {integer} [kwargs.offset]
     * @returns {Object[]}
     */
    _mockReadGroup: function (model, kwargs) {
        if (!('lazy' in kwargs)) {
            kwargs.lazy = true;
        }
        var self = this;
        var fields = this.data[model].fields;
        var aggregatedFields = [];
        _.each(kwargs.fields, function (field) {
            var split = field.split(":");
            var fieldName = split[0];
            if (kwargs.groupby.indexOf(fieldName) > 0) {
                // grouped fields are not aggregated
                return;
            }
            if (fields[fieldName] && (fields[fieldName].type === 'many2one') && split[1] !== 'count_distinct') {
                return;
            }
            aggregatedFields.push(fieldName);
        });
        var groupBy = [];
        if (kwargs.groupby.length) {
            groupBy = kwargs.lazy ? [kwargs.groupby[0]] : kwargs.groupby;
        }
        var records = this._getRecords(model, kwargs.domain);

        // if no fields have been given, the server picks all stored fields
        if (kwargs.fields.length === 0) {
            aggregatedFields = _.keys(this.data[model].fields);
        }

        var groupByFieldNames = _.map(groupBy, function (groupByField) {
            return groupByField.split(":")[0];
        });

        // filter out non existing fields
        aggregatedFields = _.filter(aggregatedFields, function (name) {
            return name in self.data[model].fields && !(_.contains(groupByFieldNames,name));
        });

        function aggregateFields(group, records) {
            var type;
            for (var i = 0; i < aggregatedFields.length; i++) {
                type = fields[aggregatedFields[i]].type;
                if (type === 'float' || type === 'integer') {
                    group[aggregatedFields[i]] = null;
                    for (var j = 0; j < records.length; j++) {
                        var value = group[aggregatedFields[i]] || 0;
                        group[aggregatedFields[i]] = value + records[j][aggregatedFields[i]];
                    }
                }
                if (type === 'many2one') {
                    var ids = _.pluck(records, aggregatedFields[i]);
                    group[aggregatedFields[i]] = _.uniq(ids).length || null;
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
                } else if (aggregateFunction === 'week') {
                    return moment(val).format('ww YYYY');
                } else if (aggregateFunction === 'quarter') {
                    return 'Q' + moment(val).format('Q YYYY');
                } else if (aggregateFunction === 'year') {
                    return moment(val).format('Y');
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
                    value += formatValue(groupByField, record[fieldName]);
                } else {
                    value += JSON.stringify(record[groupByField]);
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

                if (field.type === 'date' && val) {
                    var aggregateFunction = groupByField.split(':')[1];
                    var startDate, endDate;
                    if (aggregateFunction === 'day') {
                        startDate = moment(val, 'YYYY-MM-DD');
                        endDate = startDate.clone().add(1, 'days');
                    } else if (aggregateFunction === 'week') {
                        startDate = moment(val, 'ww YYYY');
                        endDate = startDate.clone().add(1, 'weeks');
                    } else if (aggregateFunction === 'year') {
                        startDate = moment(val, 'Y');
                        endDate = startDate.clone().add(1, 'years');
                    } else {
                        startDate = moment(val, 'MMMM YYYY');
                        endDate = startDate.clone().add(1, 'months');
                    }
                    res.__domain = [[fieldName, '>=', startDate.format('YYYY-MM-DD')], [fieldName, '<', endDate.format('YYYY-MM-DD')]].concat(res.__domain);
                } else {
                    res.__domain = [[fieldName, '=', val]].concat(res.__domain);
                }

            });

            // compute count key to match dumb server logic...
            var countKey;
            const groupByNoLeaf = kwargs.context ? 'group_by_no_leaf' in kwargs.context : false;
            if (kwargs.lazy && (groupBy.length >= 2 || !groupByNoLeaf)) {
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
            result = this._sortByField(result, model, fieldName, order);
        }

        if (kwargs.limit) {
            var offset = kwargs.offset || 0;
            result = result.slice(offset, kwargs.limit + offset);
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
        var groupBy = kwargs.group_by;
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
     * Simulates a 'resequence' operation
     *
     * @private
     * @param {string} model
     * @param {string} field
     * @param {Array} ids
     */
    _mockResequence: function (args) {
        var offset = args.offset ? Number(args.offset) : 0;
        var field = args.field ? args.field : 'sequence';
        var records = this.data[args.model].records;
        if (!(field in this.data[args.model].fields)) {
            return false;
        }
        for (var i in args.ids) {
            var record = _.findWhere(records, {id: args.ids[i]});
            record[field] = Number(i) + offset;
        }
        return true;
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
            fields: kwargs.fields || args[1],
            offset: kwargs.offset || args[2],
            limit: kwargs.limit || args[3],
            sort: kwargs.order || args[4],
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
        var fields = args.fields && args.fields.length ? args.fields : _.keys(this.data[args.model].fields);
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
            // warning: only consider first level of sort
            args.sort = args.sort.split(',')[0];
            var fieldName = args.sort.split(' ')[0];
            var order = args.sort.split(' ')[1];
            processedRecords = this._sortByField(processedRecords, args.model, fieldName, order);
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
     * Simulate a 'web_read_group' call to the server.
     *
     * Note: some keys in kwargs are still ignored
     *
     * @private
     * @param {string} model a string describing an existing model
     * @param {Object} kwargs various options supported by read_group
     * @param {string[]} kwargs.groupby fields that we are grouping
     * @param {string[]} kwargs.fields fields that we are aggregating
     * @param {Array} kwargs.domain the domain used for the read_group
     * @param {boolean} kwargs.lazy still mostly ignored
     * @param {integer} [kwargs.limit]
     * @param {integer} [kwargs.offset]
     * @param {boolean} [kwargs.expand=false] if true, read records inside each
     *   group
     * @param {integer} [kwargs.expand_limit]
     * @param {integer} [kwargs.expand_orderby]
     * @returns {Object[]}
     */
    _mockWebReadGroup: function (model, kwargs) {
        var self = this;
        var groups = this._mockReadGroup(model, kwargs);
        if (kwargs.expand && kwargs.groupby.length === 1) {
            groups.forEach(function (group) {
                group.__data = self._mockSearchReadController({
                    domain: group.__domain,
                    model: model,
                    fields: kwargs.fields,
                    limit: kwargs.expand_limit,
                    order: kwargs.expand_orderby,
                });
            });
        }
        var allGroups = this._mockReadGroup(model, {
            domain: kwargs.domain,
            fields: ['display_name'],
            groupby: kwargs.groupby,
            lazy: kwargs.lazy,
        });
        return {
            groups: groups,
            length: allGroups.length,
        };
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
     * @returns {Promise<any>}
     *          Resolved with the result of the RPC. If the RPC should fail, the
     *          promise should either be rejected or the call should throw an
     *          exception (@see performRpc for error handling).
     */
    _performRpc: function (route, args) {
        switch (route) {
            case '/web/action/load':
                return Promise.resolve(this._mockLoadAction(args.kwargs));

            case '/web/dataset/search_read':
                return Promise.resolve(this._mockSearchReadController(args));

            case '/web/dataset/resequence':
                return Promise.resolve(this._mockResequence(args));
        }
        if (route.indexOf('/web/image') >= 0 || _.contains(['.png', '.jpg'], route.substr(route.length - 4))) {
            return Promise.resolve();
        }
        switch (args.method) {
            case 'copy':
                return Promise.resolve(this._mockCopy(args.model, args.args[0]));

            case 'create':
                return Promise.resolve(this._mockCreate(args.model, args.args[0]));

            case 'default_get':
                return Promise.resolve(this._mockDefaultGet(args.model, args.args, args.kwargs));

            case 'fields_get':
                return Promise.resolve(this._mockFieldsGet(args.model, args.args));

            case 'search_panel_select_range':
                return Promise.resolve(this._mockSearchPanelSelectRange(args.model, args.args, args.kwargs));

            case 'search_panel_select_multi_range':
                return Promise.resolve(this._mockSearchPanelSelectMultiRange(args.model, args.args, args.kwargs));

            case 'load_views':
                return Promise.resolve(this._mockLoadViews(args.model, args.kwargs));

            case 'name_get':
                return Promise.resolve(this._mockNameGet(args.model, args.args));

            case 'name_create':
                return Promise.resolve(this._mockNameCreate(args.model, args.args));

            case 'name_search':
                return Promise.resolve(this._mockNameSearch(args.model, args.args, args.kwargs));

            case 'onchange':
                return Promise.resolve(this._mockOnchange(args.model, args.args));

            case 'read':
                return Promise.resolve(this._mockRead(args.model, args.args, args.kwargs));

            case 'read_group':
                return Promise.resolve(this._mockReadGroup(args.model, args.kwargs));

            case 'web_read_group':
                return Promise.resolve(this._mockWebReadGroup(args.model, args.kwargs));

            case 'read_progress_bar':
                return Promise.resolve(this._mockReadProgressBar(args.model, args.kwargs));

            case 'search_count':
                return Promise.resolve(this._mockSearchCount(args.model, args.args));

            case 'search_read':
                return Promise.resolve(this._mockSearchRead(args.model, args.args, args.kwargs));

            case 'unlink':
                return Promise.resolve(this._mockUnlink(args.model, args.args));

            case 'write':
                return Promise.resolve(this._mockWrite(args.model, args.args));
        }
        var model = this.data[args.model];
        if (model && typeof model[args.method] === 'function') {
            return Promise.resolve(this.data[args.model][args.method](args.args, args.kwargs));
        }

        throw new Error("Unimplemented route: " + route);
    },
    /**
     * @private
     * @param {Object[]} records the records to sort
     * @param {string} model the model of records
     * @param {string} fieldName the field to sort on
     * @param {string} [order="DESC"] "ASC" or "DESC"
     * @returns {Object}
     */
    _sortByField: function (records, model, fieldName, order) {
        const field = this.data[model].fields[fieldName];
        records.sort((r1, r2) => {
            let v1 = r1[fieldName];
            let v2 = r2[fieldName];
            if (field.type === 'many2one') {
                const coRecords = this.data[field.relation].records;
                if (this.data[field.relation].fields.sequence) {
                    // use sequence field of comodel to sort records
                    v1 = coRecords.find(r => r.id === v1[0]).sequence;
                    v2 = coRecords.find(r => r.id === v2[0]).sequence;
                } else {
                    // sort by id
                    v1 = v1[0];
                    v2 = v2[0];
                }
            }
            if (v1 < v2) {
                return order === 'ASC' ? -1 : 1;
            }
            if (v1 > v2) {
                return order === 'ASC' ? 1 : -1;
            }
            return 0;
        });
        return records;
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
            _.each(tree.childNodes, function (c) { self._traverse(c, f); });
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
