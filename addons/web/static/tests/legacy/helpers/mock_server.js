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
                const values = model.records[i];
                // add potentially missing id
                const id = values.id === undefined
                    ? this._getUnusedID(modelName) :
                    values.id;
                // create a clean object, initial values are passed to write
                model.records[i] = { id };
                // ensure initial data goes through proper conversion (x2m, ...)
                this._applyDefaults(model, values);
                this._writeRecord(modelName, values, id, {
                    ensureIntegrity: false,
                });
            }
        }
        // used to prevent _updateComodelRelationalFields to be trigerred during
        // initial record creation.
        this.isInitialized = true;

        // fill relational fields' inverse.
        for (const modelName in this.data) {
            this.data[modelName].records.forEach(record => this._updateComodelRelationalFields(modelName, record));
        }
        this.debug = options.debug;

        this.currentDate = options.currentDate || moment().format("YYYY-MM-DD");

        this.actions = options.actions || [];
        this.archs = options.archs || {};
    },

    /**
     * Perform asynchronous setup after the initialization of the mockServer.
     */
    setup: async function () {},

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
     * 'view_get' call to the server. Calls processViews() of data_manager
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
    getView: function (params) {
        var model = params.model;
        var toolbar = params.toolbar;
        var viewId = params.view_id;
        var viewOptions = params.viewOptions || {};
        if (!(model in this.data)) {
            throw new Error('Model ' + model + ' was not defined in mock server data');
        }
        var fields = $.extend(true, {}, this.data[model].fields);
        var view = this._getView(params.arch, model, fields, viewOptions.context || {});
        if (toolbar) {
            view.toolbar = toolbar;
        }
        if (viewId) {
            view.id = viewId;
        }
        return view;
    },
    /**
     * Simulates a complete fetch call.
     *
     * @param {string} resource
     * @param {Object} init
     * @returns {any}
     */
    async performFetch(resource, init) {
        if (this.debug) {
            console.log(
                '%c[fetch] request ' + resource, 'color: blue; font-weight: bold;',
                JSON.parse(JSON.stringify(init))
            );
        }
        const res = await this._performFetch(resource, init);
        if (this.debug) {
            console.log('%c[fetch] response' + resource, 'color: blue; font-weight: bold;', res);
        }
        return res;
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
            abort = function (rejectError = true) {
                if (rejectError) {
                    throw new Error("XmlHttpRequestError abort");
                }
            }
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
            var errorString = typeof message !== "string" ? JSON.stringify(message || false) : message;
            if (debug) {
                console.warn(
                    '%c[rpc] response (error) %s%s, during test %s',
                    'color: orange; font-weight: bold;',
                    route,
                    message != null && ` -> ${errorString}`,
                    JSON.stringify(QUnit.config.current.testName)
                );
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
                    const def = model.fields[fieldName].default;
                    record[fieldName] = typeof def === 'function' ? def.call(this) : def;
                } else if (_.contains(['one2many', 'many2many'], model.fields[fieldName].type)) {
                    record[fieldName] = [];
                } else {
                    record[fieldName] = false;
                }
            }
        }
    },
    /**
     * Converts an Object representing a record to actual return Object of the
     * python `onchange` method.
     * Specifically, it applies `name_get` on many2one's and transforms raw id
     * list in orm command lists for x2many's.
     * For x2m fields that add or update records (ORM commands 0 and 1), it is
     * recursive.
     *
     * @private
     * @param {string} model: the model's name
     * @param {Object} values: an object representing a record
     * @returns {Object}
     */
    _convertToOnChange(model, values) {
        Object.entries(values).forEach(([fname, val]) => {
            const field = this.data[model].fields[fname];
            if (field.type === 'many2one' && typeof val === 'number') {
                // implicit name_get
                const m2oRecord = this.data[field.relation].records.find(r => r.id === val);
                values[fname] = [val, m2oRecord.display_name];
            } else if (field.type === 'one2many' || field.type === 'many2many') {
                // TESTS ONLY
                // one2many_ids = [1,2,3] is a simpler way to express it than orm commands
                const isCommandList = val.length && Array.isArray(val[0]);
                if (!isCommandList) {
                    values[fname] = [[6, false, val]];
                } else {
                    val.forEach(cmd => {
                        if (cmd[0] === 0 || cmd[0] === 1) {
                            cmd[2] = this._convertToOnChange(field.relation, cmd[2]);
                        }
                    });
                }
            }
        });
        return values;
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
     * 'get_view' call to the server.
     *
     * @private
     * @param {string} arch a string OR a parsed xml document
     * @param {string} model a model name (that should be in this.data)
     * @param {Object} fields
     * @param {Object} context
     * @returns {Object} an object with 2 keys: arch and fields (the fields
     *   appearing in the views)
     */
    _getView: function (arch, model, fields, context) {
        var self = this;
        var modifiersNames = ['invisible', 'readonly', 'required'];
        var onchanges = this.data[model].onchanges || {};
        var fieldNodes = {};
        var groupbyNodes = {};
        const relatedModels = new Set([model]);

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

            const inListHeader = inTreeView && node.closest('header');
            _.each(modifiersNames, function (a) {
                var mod = node.getAttribute(a);
                if (mod) {
                    var pyevalContext = window.py.dict.fromJSON(context || {});
                    var v = pyUtils.py_eval(mod, {context: pyevalContext}) ? true: false;
                    if (inTreeView && !inListHeader && a === 'invisible') {
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

        let relModel, relFields;
        _.each(fieldNodes, function (node, name) {
            var field = fields[name];
            if (field.type === "many2one" || field.type === "many2many") {
                var canCreate = node.getAttribute('can_create');
                node.setAttribute('can_create', canCreate || "true");
                var canWrite = node.getAttribute('can_write');
                node.setAttribute('can_write', canWrite || "true");
            }
            if (field.type === "one2many" || field.type === "many2many") {
                relModel = field.relation;
                relatedModels.add(relModel);
                _.each(node.childNodes, function (childNode) {
                    if (childNode.tagName) { // skip text nodes
                        relFields = $.extend(true, {}, self.data[relModel].fields);
                        // this is hackhish, but _getView modifies the subview document in place,
                        // especially to generate the "modifiers" attribute
                        const { models } = self._getView(childNode, relModel,
                            relFields, _.extend({}, context, {base_model_name: model}));
                        [...models].forEach((modelName) => relatedModels.add(modelName));
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
            relatedModels.add(relModel);
            relFields = $.extend(true, {}, self.data[relModel].fields);
            node._isProcessed = true;
            // postprocess simulation
            const { models } = self._getView(node, relModel, relFields, context);
            [...models].forEach((modelName) => relatedModels.add(modelName));
        });

        var xmlSerializer = new XMLSerializer();
        var processedArch = xmlSerializer.serializeToString(doc);
        return {
            arch: processedArch,
            model: model,
            type: doc.tagName === 'tree' ? 'list' : doc.tagName,
            models: relatedModels,
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
     * @param {Object} [params={}]
     * @param {boolean} [params.active_test=true]
     * @returns {Object[]} a list of records
     */
    _getRecords: function (model, domain, { active_test = true } = {}) {
        if (!_.isArray(domain)) {
            throw new Error("MockServer._getRecords: given domain has to be an array.");
        }

        var self = this;
        var records = this.data[model].records;

        if (active_test && 'active' in this.data[model].fields) {
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
            domain = domain.map((criterion) => {
                // 'child_of' operator isn't supported by domain.js, so we replace
                // in by the 'in' operator (with the ids of children)
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
                // In case of many2many field, if domain operator is '=' generally change it to 'in' operator
                const field = this.data[model].fields[criterion[0]] || {};
                if (field.type === "many2many" && criterion[1] === "=") {
                    if (criterion[2] === false) {
                        // if undefined value asked, domain.js require equality with empty array
                        criterion = [criterion[0], "=", []];
                    } else {
                        criterion = [criterion[0], "in", [criterion[2]]];
                    }
                }
                return criterion;
            });
            records = _.filter(records, function (record) {
                return self._evaluateDomain(domain, record);
            });
        }

        return records;
    },
    /**
     * Helper function, to find an available ID. The current algorithm is to
     * return the currently highest id + 1.
     *
     * @private
     * @param {string} modelName
     * @returns {integer} a valid ID (> 0)
     */
    _getUnusedID: function (modelName) {
        var model = this.data[modelName];
        return model.records.reduce((max, record) => {
            if (!Number.isInteger(record.id)) {
                return max;
            }
            return Math.max(record.id, max);
        }, 0) + 1;
    },
    /**
     * Simulate a 'call_button' operation from a view.
     *
     * @private
     * @param {Object} param0
     * @param {Array<integer[]>} param0.args
     * @param {Object} [param0.kargs]
     * @param {string} param0.method
     * @param {string} param0.model
     * @returns {any}
     * @throws {Error} in case the call button of provided model/method is not
     *   implemented.
     */
    _mockCallButton({ args, kwargs, method, model }) {
        throw new Error(`Unimplemented mocked call button on "${model}"/"${method}"`);
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
            throw new Error("Cannot create a record with a predefinite id");
        }
        var model = this.data[modelName];
        var id = this._getUnusedID(modelName);
        var record = {id: id};
        model.records.push(record);
        this._applyDefaults(model, values);
        this._writeRecord(modelName, values, id);
        if (this.isInitialized) {
            this._updateComodelRelationalFields(modelName, record);
        }
        return id;
    },
    /**
     * Simulate a 'default_get' operation
     *
     * @private
     * @param {string} modelName
     * @param {array[]} args a list with a list of fields in the first position
     * @param {Object} [kwargs={}]
     * @param {Object} [kwargs.context] the context to eventually read default
     *   values
     * @returns {Object}
     */
    _mockDefaultGet: function (modelName, args, kwargs = {}) {
        const fields = args[0];
        const model = this.data[modelName];
        const result = {};
        for (const fieldName of fields) {
            const key = "default_" + fieldName;
            if (kwargs.context && key in kwargs.context) {
                result[fieldName] = kwargs.context[key];
                continue;
            }
            const field = model.fields[fieldName];
            if ('default' in field) {
                result[fieldName] = field.default;
                continue;
            }
        }
        for (const fieldName in result) {
            const field = model.fields[fieldName];
            if (field.type === "many2one") {
                const recordExists = this.data[field.relation].records.some(
                    (r) => r.id === result[fieldName]
                );
                if (!recordExists) {
                    delete result[fieldName];
                }
            }
        }
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
     * Simulates a call to the server '_search_panel_field_image' method.
     *
     * @private
     * @param {string} model
     * @param {string} fieldName
     * @param {Object} kwargs
     * @see _mockSearchPanelDomainImage()
     */
	_mockSearchPanelFieldImage(model, fieldName, kwargs) {
        const enableCounters = kwargs.enable_counters;
        const onlyCounters = kwargs.only_counters;
        const extraDomain = kwargs.extra_domain || [];
        const normalizedExtra = Domain.prototype.normalizeArray(extraDomain);
        const noExtra = JSON.stringify(normalizedExtra) === "[]";
        const modelDomain = kwargs.model_domain || [];
        const countDomain = Domain.prototype.normalizeArray([
            ...modelDomain,
            ...extraDomain,
        ]);

        const limit = kwargs.limit;
        const setLimit = kwargs.set_limit;

        if (onlyCounters) {
            return this._mockSearchPanelDomainImage(model, fieldName, countDomain, true);
        }

        const modelDomainImage = this._mockSearchPanelDomainImage(
            model,
            fieldName,
            modelDomain,
            enableCounters && noExtra,
            setLimit && limit
        );
        if (enableCounters && !noExtra) {
            const countDomainImage = this._mockSearchPanelDomainImage(
                model,
                fieldName,
                countDomain,
                true
            );
            for (const [id, values] of modelDomainImage.entries()) {
                const element = countDomainImage.get(id);
                values.__count = element ? element.__count : 0;
            }
        }

        return modelDomainImage;
    },

    /**
     * Simulates a call to the server '_search_panel_domain_image' method.
     *
     * @private
     * @param {string} model
     * @param {Array[]} domain
     * @param {string} fieldName
     * @param {boolean} setCount
     * @returns {Map}
     */
    _mockSearchPanelDomainImage: function (model, fieldName, domain, setCount=false, limit=false) {
        const field = this.data[model].fields[fieldName];
        let groupIdName;
        if (field.type === 'many2one') {
            groupIdName = value => value || [false, undefined];
            // mockReadGroup does not take care of the condition [fieldName, '!=', false]
            // in the domain defined below !!!
        } else if (field.type === 'selection') {
            const selection = {};
            for (const [value, label] of this.data[model].fields[fieldName].selection) {
                selection[value] = label;
            }
            groupIdName = value => [value, selection[value]];
        }
        domain = Domain.prototype.normalizeArray([
            ...domain,
            [fieldName, '!=', false],
        ]);
        const groups = this._mockReadGroup(model, {
            domain,
            fields: [fieldName],
            groupby: [fieldName],
            limit,
        });
        const domainImage = new Map();
        for (const group of groups) {
            const [id, display_name] = groupIdName(group[fieldName]);
            const values = { id, display_name };
            if (setCount) {
                values.__count = group[fieldName + '_count'];
            }
            domainImage.set(id, values);
        }
        return domainImage;
    },
    /**
     * Simulates a call to the server '_search_panel_global_counters' method.
     *
     * @private
     * @param {Map} valuesRange
     * @param {(string|boolean)} parentName 'parent_id' or false
     */
    _mockSearchPanelGlobalCounters: function (valuesRange, parentName) {
        const localCounters = [...valuesRange.keys()].map(id => valuesRange.get(id).__count);
        for (let [id, values] of valuesRange.entries()) {
            const count = localCounters[id];
            if (count) {
                let parent_id = values[parentName];
                while (parent_id) {
                    values = valuesRange.get(parent_id);
                    values.__count += count;
                    parent_id = values[parentName];
                }
            }
        }
    },
    /**
     * Simulates a call to the server '_search_panel_sanitized_parent_hierarchy' method.
     *
     * @private
     * @param {Object[]} records
     * @param {(string|boolean)} parentName 'parent_id' or false
     * @param {number[]} ids
     * @returns {Object[]}
     */
    _mockSearchPanelSanitizedParentHierarchy: function (records, parentName, ids) {
        const getParentId = record => record[parentName] && record[parentName][0];
        const allowedRecords = {};
        for (const record of records) {
            allowedRecords[record.id] = record;
        }
        const recordsToKeep = {};
        for (const id of ids) {
            const ancestorChain = {};
            let recordId = id;
            let chainIsFullyIncluded = true;
            while (chainIsFullyIncluded && recordId) {
                const knownStatus = recordsToKeep[recordId];
                if (knownStatus !== undefined) {
                    chainIsFullyIncluded = knownStatus;
                    break;
                }
                const record = allowedRecords[recordId];
                if (record) {
                    ancestorChain[recordId] = record;
                    recordId = getParentId(record);
                } else {
                    chainIsFullyIncluded = false;
                }
            }
            for (const id in ancestorChain) {
                recordsToKeep[id] = chainIsFullyIncluded;
            }
        }
        return records.filter(rec => recordsToKeep[rec.id]);
    },
    /**
     * Simulates a call to the server 'search_panel_selection_range' method.
     *
     * @private
     * @param {string} model
     * @param {string} fieldName
     * @param {Object} kwargs
     * @returns {Object[]}
     */
    _mockSearchPanelSelectionRange: function (model, fieldName, kwargs) {
        const enableCounters = kwargs.enable_counters;
        const expand = kwargs.expand;
        let domainImage;
        if (enableCounters || !expand) {
            const newKwargs = Object.assign({}, kwargs, {
                only_counters: expand,
            });
            domainImage = this._mockSearchPanelFieldImage(model, fieldName, newKwargs);
        }
        if (!expand) {
            return [...domainImage.values()];
        }
        const selection = this.data[model].fields[fieldName].selection;
        const selectionRange = [];
        for (const [value, label] of selection) {
            const values = {
                id: value,
                display_name: label,
            };
            if (enableCounters) {
                values.__count = domainImage.get(value) ? domainImage.get(value).__count : 0;
            }
            selectionRange.push(values);
        }
        return selectionRange;
    },
    /**
     * Simulates a call to the server 'search_panel_select_range' method.
     *
     * @private
     * @param {string} model
     * @param {string[]} args
     * @param {string} args[fieldName]
     * @param {Object} [kwargs={}]
     * @param {Array[]} [kwargs.category_domain] domain generated by categories
     *      (this parameter is used in _search_panel_range)
     * @param {Array[]} [kwargs.comodel_domain] domain of field values (if relational)
     *      (this parameter is used in _search_panel_range)
     * @param {boolean} [kwargs.enable_counters] whether to count records by value
     * @param {Array[]} [kwargs.filter_domain] domain generated by filters
     * @param {integer} [kwargs.limit] maximal number of values to fetch
     * @param {Array[]} [kwargs.search_domain] base domain of search (this parameter
     *      is used in _search_panel_range)
     * @returns {Object}
     */
    _mockSearchPanelSelectRange: function (model, [fieldName], kwargs) {
        const field = this.data[model].fields[fieldName];
        const supportedTypes = ['many2one', 'selection'];
        if (!supportedTypes.includes(field.type)) {
            throw new Error(`Only types ${supportedTypes} are supported for category (found type ${field.type})`);
        }

        const modelDomain = kwargs.search_domain || [];
        const extraDomain = Domain.prototype.normalizeArray([
            ...(kwargs.category_domain || []),
            ...(kwargs.filter_domain || []),
        ]);

        if (field.type === 'selection') {
            const newKwargs = Object.assign({}, kwargs, {
                model_domain: modelDomain,
                extra_domain: extraDomain,
            });
            kwargs.model_domain = modelDomain;
            return {
                parent_field: false,
                values: this._mockSearchPanelSelectionRange(model, fieldName, newKwargs),
            };
        }

        const fieldNames = ['display_name'];
        let hierarchize = 'hierarchize' in kwargs ? kwargs.hierarchize : true;
        let getParentId;
        let parentName = false;
        if (hierarchize && this.data[field.relation].fields.parent_id) {
            parentName = 'parent_id'; // in tests, parent field is always 'parent_id'
            fieldNames.push(parentName);
            getParentId = record => record.parent_id && record.parent_id[0];
        } else {
            hierarchize = false;
        }
        let comodelDomain = kwargs.comodel_domain || [];
        const enableCounters = kwargs.enable_counters;
        const expand = kwargs.expand;
        const limit = kwargs.limit;
        let domainImage;
        if (enableCounters || !expand) {
            const newKwargs = Object.assign({}, kwargs, {
                model_domain: modelDomain,
                extra_domain: extraDomain,
                only_counters: expand,
                set_limit: limit && !(expand || hierarchize || comodelDomain),
            });
            domainImage = this._mockSearchPanelFieldImage(model, fieldName, newKwargs);
        }
        if (!expand && !hierarchize && !comodelDomain.length) {
            if (limit && domainImage.size === limit) {
                return { error_msg: "Too many items to display." };
            }
            return {
                parent_field: parentName,
                values: [...domainImage.values()],
            };
        }
        let imageElementIds;
        if (!expand) {
            imageElementIds = [...domainImage.keys()].map(Number);
            let condition;
            if (hierarchize) {
                const records = this.data[field.relation].records;
                const ancestorIds = new Set();
                for (const id of imageElementIds) {
                    let recordId = id;
                    let record;
                    while (recordId) {
                        ancestorIds.add(recordId);
                        record = records.find(rec => rec.id === recordId);
                        recordId = record[parentName];
                    }
                }
                condition = ['id', 'in', [...new Set(ancestorIds)]];
            } else {
                condition = ['id', 'in', imageElementIds];
            }
            comodelDomain = Domain.prototype.normalizeArray([
                ...comodelDomain,
                condition,
            ]);
        }
        let comodelRecords = this._mockSearchRead(field.relation, [comodelDomain, fieldNames], { limit });

        if (hierarchize) {
            const ids = expand ? comodelRecords.map(rec => rec.id) : imageElementIds;
            comodelRecords = this._mockSearchPanelSanitizedParentHierarchy(comodelRecords, parentName, ids);
        }

        if (limit && comodelRecords.length === limit) {
            return { error_msg: "Too many items to display." };
        }
        // A map is used to keep the initial order.
        const fieldRange = new Map();
        for (const record of comodelRecords) {
            const values = {
                id: record.id,
                display_name: record.display_name,
            };
            if (hierarchize) {
                values[parentName] = getParentId(record);
            }
            if (enableCounters) {
                values.__count = domainImage.get(record.id) ? domainImage.get(record.id).__count : 0;
            }
            fieldRange.set(record.id, values);
        }

        if (hierarchize && enableCounters) {
            this._mockSearchPanelGlobalCounters(fieldRange, parentName);
        }

        return {
            parent_field: parentName,
            values: [...fieldRange.values()],
        };
    },
    /**
     * Simulates a call to the server 'search_panel_select_multi_range' method.
     *
     * @private
     * @param {string} model
     * @param {string[]} args
     * @param {string} args[fieldName]
     * @param {Object} [kwargs={}]
     * @param {Array[]} [kwargs.category_domain] domain generated by categories
     * @param {Array[]} [kwargs.comodel_domain] domain of field values (if relational)
     *      (this parameter is used in _search_panel_range)
     * @param {boolean} [kwargs.enable_counters] whether to count records by value
     * @param {Array[]} [kwargs.filter_domain] domain generated by filters
     * @param {string} [kwargs.group_by] extra field to read on comodel, to group
     *      comodel records
     * @param {Array[]} [kwargs.group_domain] dict, one domain for each activated
     *      group for the group_by (if any). Those domains are used to fech accurate
     *      counters for values in each group
     * @param {integer} [kwargs.limit] maximal number of values to fetch
     * @param {Array[]} [kwargs.search_domain] base domain of search
     * @returns {Object}
     */
    _mockSearchPanelSelectMultiRange: function (model, [fieldName], kwargs) {
        const field = this.data[model].fields[fieldName];
        const supportedTypes = ['many2one', 'many2many', 'selection'];
        if (!supportedTypes.includes(field.type)) {
            throw new Error(`Only types ${supportedTypes} are supported for filter (found type ${field.type})`);
        }
        let modelDomain = kwargs.search_domain || [];
        let extraDomain = Domain.prototype.normalizeArray([
            ...(kwargs.category_domain || []),
            ...(kwargs.filter_domain || []),
        ]);
        if (field.type === 'selection') {
            const newKwargs = Object.assign({}, kwargs, {
                model_domain: modelDomain,
                extra_domain: extraDomain,
            });
            return {
                values: this._mockSearchPanelSelectionRange(model, fieldName, newKwargs),
            };
        }
        const fieldNames = ['display_name'];
        const groupBy = kwargs.group_by;
        let groupIdName;
        if (groupBy) {
            const groupByField = this.data[field.relation].fields[groupBy];
            fieldNames.push(groupBy);
            if (groupByField.type === 'many2one') {
                groupIdName = value => value || [false, "Not set"];
            } else if (groupByField.type === 'selection') {
                const groupBySelection = Object.assign({}, this.data[field.relation].fields[groupBy].selection);
                groupBySelection[false] = "Not Set";
                groupIdName = value => [value, groupBySelection[value]];
            } else {
                groupIdName = value => value ? [value, value] : [false, "Not set"];
            }
        }
        let comodelDomain = kwargs.comodel_domain || [];
        const enableCounters = kwargs.enable_counters;
        const expand = kwargs.expand;
        const limit = kwargs.limit;
        if (field.type === 'many2many') {
            const comodelRecords = this._mockSearchRead(field.relation, [comodelDomain, fieldNames], { limit });
            if (expand && limit && comodelRecords.length === limit) {
                return { error_msg: "Too many items to display." };
            }

            const groupDomain = kwargs.group_domain;
            const fieldRange = [];
            for (const record of comodelRecords) {
                const values= {
                    id: record.id,
                    display_name: record.display_name,
                };
                let groupId;
                if (groupBy) {
                    const [gId, gName] = groupIdName(record[groupBy]);
                    values.group_id = groupId = gId;
                    values.group_name = gName;
                }
                let count;
                let inImage;
                if (enableCounters || !expand) {
                    const searchDomain = Domain.prototype.normalizeArray([
                        ...modelDomain,
                        [fieldName, "in", record.id]
                    ]);
                    let localExtraDomain = extraDomain;
                    if (groupBy && groupDomain) {
                        localExtraDomain = Domain.prototype.normalizeArray([
                            ...localExtraDomain,
                            ...(groupDomain[JSON.stringify(groupId)] || []),
                        ]);
                    }
                    const searchCountDomain = Domain.prototype.normalizeArray([
                        ...searchDomain,
                        ...localExtraDomain,
                    ]);
                    if (enableCounters) {
                        count = this._mockSearchCount(model, [searchCountDomain]);
                    }
                    if (!expand) {
                        if (
                            enableCounters &&
                            JSON.stringify(localExtraDomain) === "[]"
                        ) {
                            inImage = count;
                        } else {
                            inImage = (this._mockSearch(model, [searchDomain], { limit: 1 })).length;
                        }
                    }
                }
                if (expand || inImage) {
                    if (enableCounters) {
                        values.__count = count;
                    }
                    fieldRange.push(values);
                }
            }

            if (!expand && limit && fieldRange.length === limit) {
                return { error_msg: "Too many items to display." };
            }

            return { values: fieldRange };
        }

        if (field.type === 'many2one') {
            let domainImage;
            if (enableCounters || !expand) {
                extraDomain = Domain.prototype.normalizeArray([
                    ...extraDomain,
                    ...(kwargs.group_domain || []),
                ]);
                modelDomain = Domain.prototype.normalizeArray([
                    ...modelDomain,
                    ...(kwargs.group_domain || []),
                ]);
                const newKwargs = Object.assign({}, kwargs, {
                    model_domain: modelDomain,
                    extra_domain: extraDomain,
                    only_counters: expand,
                    set_limit: limit && !(expand || groupBy || comodelDomain),
                });
                domainImage = this._mockSearchPanelFieldImage(model, fieldName, newKwargs);
            }
            if (!expand && !groupBy && !comodelDomain.length) {
                if (limit && domainImage.size === limit) {
                    return { error_msg: "Too many items to display." };
                }
                return { values: [...domainImage.values()] };
            }
            if (!expand) {
                const imageElementIds = [...domainImage.keys()].map(Number);
                comodelDomain = Domain.prototype.normalizeArray([
                    ...comodelDomain,
                    ['id', 'in', imageElementIds],
                ]);
            }
            const comodelRecords = this._mockSearchRead(field.relation, [comodelDomain, fieldNames], { limit });
            if (limit && comodelRecords.length === limit) {
                return { error_msg: "Too many items to display." };
            }

            const fieldRange = [];
            for (const record of comodelRecords) {
                const values= {
                    id: record.id,
                    display_name: record.display_name,
                };
                if (groupBy) {
                    const [groupId, groupName] = groupIdName(record[groupBy]);
                    values.group_id = groupId;
                    values.group_name = groupName;
                }
                if (enableCounters) {
                    values.__count = domainImage.get(record.id) ? domainImage.get(record.id).__count : 0;
                }
                fieldRange.push(values);
            }
            return { values: fieldRange };
        }
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
            console.warn(`No action found for ID ${kwargs.action_id} during test ${QUnit.config.current.testName} (legacy)`);
        }
        return action || false;
    },
    /**
     * Simulate a 'get_views' operation
     *
     * @param {string} model
     * @param {Array} args
     * @param {Object} kwargs
     * @param {Array} kwargs.views
     * @param {Object} kwargs.options
     * @param {Object} kwargs.context
     * @returns {Object}
     */
    _mockGetViews: function (model, kwargs) {
        var self = this;
        var views = {};
        _.each(kwargs.views, function (view_descr) {
            var viewID = view_descr[0] || false;
            var viewType = view_descr[1];
            if (!viewID) {
                var contextKey = (viewType === 'list' ? 'tree' : viewType) + '_view_ref';
                if (contextKey in kwargs.context) {
                    viewID = parseInt(kwargs.context[contextKey]);
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
        if (!args.length) {
            throw new Error("name_get: expected one argument");
        }
        else if (!ids) {
            return []
        }
        if (!_.isArray(ids)) {
            ids = [ids];
        }
        var records = this.data[model].records;
        var names = _.map(ids, function (id) {
            return id ? [id, _.findWhere(records, {id: id}).display_name] : [null, ""];
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
     * @param {Object} args
     * @param {Object} args[1] the current record data
     * @param {string|string[]} [args[2]] a list of field names, or just a field name
     * @param {Object} args[3] the onchange spec
     * @param {Object} [kwargs]
     * @returns {Object}
     */
    _mockOnchange: function (model, args, kwargs) {
        const currentData = args[1];
        let fields = args[2];
        const onChangeSpec = args[3];
        var onchanges = this.data[model].onchanges || {};

        if (fields && !(fields instanceof Array)) {
            fields = [fields];
        }
        const firstOnChange = !fields || !fields.length;
        const onchangeVals = {};
        let defaultVals;
        let nullValues;
        if (firstOnChange) {
            const fieldsFromView = Object.keys(onChangeSpec).reduce((acc, fname) => {
                fname = fname.split('.', 1)[0];
                if (!acc.includes(fname)) {
                    acc.push(fname);
                }
                return acc;
            }, []);
            const defaultingFields = fieldsFromView.filter(fname => !(fname in currentData));
            defaultVals = this._mockDefaultGet(model, [defaultingFields], kwargs);
            // It is the new semantics: no field in arguments means we are in
            // a default_get + onchange situation
            fields = fieldsFromView;
            nullValues = {};
            fields.filter(fName => !Object.keys(defaultVals).includes(fName)).forEach(fName => {
                nullValues[fName] = false;
            });
        }
        Object.assign(currentData, defaultVals);
        fields.forEach(field => {
            if (field in onchanges) {
                const changes = Object.assign({}, nullValues, currentData);
                onchanges[field](changes);
                Object.entries(changes).forEach(([key, value]) => {
                    if (currentData[key] !== value) {
                        onchangeVals[key] = value;
                    }
                });
            }
        });

        return {
            value: this._convertToOnChange(model, Object.assign({}, defaultVals, onchangeVals)),
        };
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
                throw new Error("mock read: falsy value given as id, would result in an access error in actual server !");
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
            if (val === false || val === undefined) {
                return false;
            }
            const [fieldName, aggregateFunction = "month"] = groupByField.split(':');
            const { type } = fields[fieldName];
            if (type === "date") {
                if (aggregateFunction === 'day') {
                    return moment(val).format('YYYY-MM-DD');
                } else if (aggregateFunction === 'week') {
                    return moment(val).format('[W]WW GGGG');
                } else if (aggregateFunction === 'quarter') {
                    return moment(val).format('[Q]Q YYYY');
                } else if (aggregateFunction === 'year') {
                    return moment(val).format('Y');
                } else {
                    return moment(val).format('MMMM YYYY');
                }
            } else if (type === "datetime") {
                if (aggregateFunction === 'hour') {
                    return moment(val).format('HH[:00] DD MMM');
                } else if (aggregateFunction === 'day') {
                    return moment(val).format('YYYY-MM-DD');
                } else if (aggregateFunction === 'week') {
                    return moment(val).format('[W]WW GGGG');
                } else if (aggregateFunction === 'quarter') {
                    return moment(val).format('[Q]Q YYYY');
                } else if (aggregateFunction === 'year') {
                    return moment(val).format('Y');
                } else {
                    return moment(val).format('MMMM YYYY');
                }
            } else if (Array.isArray(val)) {
                if (val.length === 0) {
                    return false;
                }
                return type === "many2many" ? val : val[0];
            } else {
                return val;
            }
        }

        if (!groupBy.length) {
            var group = { __count: records.length };
            aggregateFields(group, records);
            return [group];
        }

        const groups = {};
        for (const r of records) {
            let recordGroupValues = [];
            for (const gbField of groupBy) {
                const [fieldName] = gbField.split(":");
                let value =formatValue(gbField, r[fieldName]);
                if (!Array.isArray(value)) {
                    value = [value];
                }
                recordGroupValues = value.reduce((acc, val) => {
                    const newGroup = {};
                    newGroup[gbField] = val;
                    if (recordGroupValues.length === 0) {
                        acc.push(newGroup);
                    } else {
                        for (const groupValue of recordGroupValues) {
                            acc.push({ ...groupValue, ...newGroup });
                        }
                    }
                    return acc;
                }, []);
            }
            for (const groupValue of recordGroupValues) {
                const valueKey = JSON.stringify(groupValue);
                groups[valueKey] = groups[valueKey] || [];
                groups[valueKey].push(r);
            }
        }

        let readGroupResult = [];
        for (const [groupId, groupRecords] of Object.entries(groups)) {
            const group = {
                ...JSON.parse(groupId),
                __domain: kwargs.domain || [],
                __range: {},
            };
            for (const gbField of groupBy) {
                if (!(gbField in group)) {
                    group[gbField] = false;
                    continue;
                }

                const [fieldName, dateRange] = gbField.split(":");
                const value = Number.isInteger(group[gbField])
                    ? group[gbField]
                    : group[gbField] || false;
                const { relation, type } = fields[fieldName];

                if (["many2one", "many2many"].includes(type) && !Array.isArray(value)) {
                    const relatedRecord = _.findWhere(this.data[relation].records, {
                        id: value
                    });
                    if (relatedRecord) {
                        group[gbField] = [value, relatedRecord.display_name];
                    } else {
                        group[gbField] = false;
                    }
                }

                if (["date", "datetime"].includes(type)) {
                    if (value) {
                        let startDate, endDate;
                        switch (dateRange) {
                            case "hour": {
                                startDate = moment(value, "HH[:00] DD MMM");
                                endDate = startDate.clone().add(1, "hours");
                                break;
                            }
                            case "day": {
                                startDate = moment(value, "YYYY-MM-DD");
                                endDate = startDate.clone().add(1, "days");
                                break;
                            }
                            case "week": {
                                startDate = moment(value, "[W]WW GGGG");
                                endDate = startDate.clone().add(1, "weeks");
                                break;
                            }
                            case "quarter": {
                                startDate = moment(value, "[Q]Q YYYY");
                                endDate = startDate.clone().add(1, "quarters");
                                break;
                            }
                            case "year": {
                                startDate = moment(value, "Y");
                                endDate = startDate.clone().add(1, "years");
                                break;
                            }
                            case "month":
                            default: {
                                startDate = moment(value, "MMMM YYYY");
                                endDate = startDate.clone().add(1, "months");
                                break;
                            }
                        }
                        const from = type === "date"
                            ? startDate.format("YYYY-MM-DD")
                            : startDate.format("YYYY-MM-DD HH:mm:ss");
                        const to = type === "date"
                            ? endDate.format("YYYY-MM-DD")
                            : endDate.format("YYYY-MM-DD HH:mm:ss");
                        // NOTE THAT the range and the domain computed here are not really accurate
                        // due to a the timezone not really taken into account.
                        // FYI, the non legacy version of the mock server handles this correctly.
                        group.__range[gbField] = { from, to };
                        group.__domain = [
                            [fieldName, ">=", from],
                            [fieldName, "<", to],
                        ].concat(group.__domain);
                    } else {
                        group.__range[gbField] = false;
                        group.__domain = [[fieldName, "=", value]].concat(group.__domain);
                    }
                } else {
                    group.__domain = [[fieldName, "=", value]].concat(group.__domain);
                }
            }
            if (_.isEmpty(group.__range)) {
                delete group.__range;
            }
            // compute count key to match dumb server logic...
            const countKey = kwargs.lazy
                ? groupBy[0].split(":")[0] + "_count"
                : "__count";
            group[countKey] = groupRecords.length;
            aggregateFields(group, groupRecords);
            readGroupResult.push(group);
        }

        if (kwargs.orderby) {
            // only consider first sorting level
            kwargs.orderby = kwargs.orderby.split(',')[0];
            const fieldName = kwargs.orderby.split(' ')[0];
            const order = kwargs.orderby.split(' ')[1];
            readGroupResult = this._sortByField(readGroupResult, model, fieldName, order);
        }

        if (kwargs.limit) {
            const offset = kwargs.offset || 0;
            readGroupResult = readGroupResult.slice(offset, kwargs.limit + offset);
        }

        return readGroupResult;
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

            // special case for bool values: rpc call response with capitalized strings
            if (!(groupByValue in data)) {
                if (groupByValue === true) {
                    groupByValue = "True";
                } else if (groupByValue === false) {
                    groupByValue = "False";
                }
            }

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
     * Simulate a 'search' operation
     *
     * @private
     * @param {string} model
     * @param {Array} args
     * @param {Object} kwargs
     * @param {integer} [kwargs.limit]
     * @returns {integer[]}
     */
    _mockSearch: function (model, args, kwargs) {
        const limit = kwargs.limit || Number.MAX_VALUE;
        const { context } = kwargs;
        const active_test =
          context && "active_test" in context ? context.active_test : true;
        return this._getRecords(model, args[0], { active_test }).map(r => r.id).slice(0, limit);
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
        const { context } = args;
        const active_test =
          context && "active_test" in context ? context.active_test : true;
        var records = this._getRecords(args.model, args.domain || [], {
          active_test,
        });
        var fields = args.fields && args.fields.length ? args.fields : _.keys(this.data[args.model].fields);
        var nbRecords = records.length;
        var offset = args.offset || 0;
        if (args.sort) {
            // warning: only consider first level of sort
            args.sort = args.sort.split(',')[0];
            var fieldName = args.sort.split(' ')[0];
            var order = args.sort.split(' ')[1];
            records = this._sortByField(records, args.model, fieldName, order);
        }
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

        // update value of relationnal fields pointing to the deleted records
        _.each(this.data, function (d) {
            var relatedFields = _.pick(d.fields, function (field) {
                return field.relation === model;
            });
            _.each(Object.keys(relatedFields), function (relatedField) {
                _.each(d.records, function (record) {
                    if (Array.isArray(record[relatedField])) {
                        record[relatedField] = _.difference(record[relatedField], ids);
                    } else if (ids.includes(record[relatedField])) {
                        record[relatedField] = false;
                    }
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
        _.each(args[0], id => {
            const originalRecord = this._mockSearchRead(model, [[['id', '=', id]]], {})[0];
            this._writeRecord(model, args[1], id);
            const updatedRecord = this.data[model].records.find(record => record.id === id);
            this._updateComodelRelationalFields(model, updatedRecord, originalRecord);
        });
        return true;
    },
    /**
     * Dispatches a fetch call to the correct helper function.
     *
     * @param {string} resource
     * @param {Object} init
     * @returns {any}
     */
    _performFetch(resource, init) {
        if (resource.match(/\/static(\/\S+\/|\/)libs?/)) {
            // every lib must be includes into the test bundle.
            return true;
        }
        if (resource.match(/\/web\/bundle\/[^.]+\.[^.]+/)) {
            // every asset must be includes into the test bundle.
            return true;
        }
        throw new Error("Unimplemented resource: " + resource);
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
    async _performRpc(route, args) {
        switch (route) {
            case '/web/dataset/call_button':
                return this._mockCallButton(args);
            case '/web/action/load':
                return this._mockLoadAction(args);

            case '/web/dataset/search_read':
                return this._mockSearchReadController(args);

            case '/web/dataset/resequence':
                return this._mockResequence(args);
        }
        if (route.indexOf('/web/image') >= 0 || _.contains(['.png', '.jpg'], route.substr(route.length - 4))) {
            return;
        }
        switch (args.method) {
            case "render_public_asset": {
                return true;
            }
            case 'copy':
                return this._mockCopy(args.model, args.args[0]);

            case 'create':
                return this._mockCreate(args.model, args.args[0]);

            case 'fields_get':
                return this._mockFieldsGet(args.model, args.args);

            case 'search_panel_select_range':
                return this._mockSearchPanelSelectRange(args.model, args.args, args.kwargs);

            case 'search_panel_select_multi_range':
                return this._mockSearchPanelSelectMultiRange(args.model, args.args, args.kwargs);

            case 'get_views':
                return this._mockGetViews(args.model, args.kwargs);

            case 'name_get':
                return this._mockNameGet(args.model, args.args);

            case 'name_create':
                return this._mockNameCreate(args.model, args.args);

            case 'name_search':
                return this._mockNameSearch(args.model, args.args, args.kwargs);

            case 'onchange':
                return this._mockOnchange(args.model, args.args, args.kwargs);

            case 'read':
                return this._mockRead(args.model, args.args, args.kwargs);

            case 'read_group':
                return this._mockReadGroup(args.model, args.kwargs);

            case 'web_read_group':
                return this._mockWebReadGroup(args.model, args.kwargs);

            case 'read_progress_bar':
                return this._mockReadProgressBar(args.model, args.kwargs);

            case 'search':
                return this._mockSearch(args.model, args.args, args.kwargs);

            case 'search_count':
                return this._mockSearchCount(args.model, args.args);

            case 'search_read':
                return this._mockSearchRead(args.model, args.args, args.kwargs);

            case 'unlink':
                return this._mockUnlink(args.model, args.args);

            case 'write':
                return this._mockWrite(args.model, args.args);
        }
        var model = this.data[args.model];
        if (model && typeof model[args.method] === 'function') {
            return this.data[args.model][args.method](args.args, args.kwargs);
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
     * Fill all inverse fields of the relational fields present in the record
     * to be created/updated.
     *
     * @param {string} modelName
     * @param {Object} record record that have been created/updated.
     * @param {Object|undefined} originalRecord record before update.
     */
     _updateComodelRelationalFields(modelName, record, originalRecord) {
        for (const fname in record) {
            const field = this.data[modelName].fields[fname];
            const comodelName = field.relation || record[field['model_name_ref_fname']];
            const inverseFieldName = field['inverse_fname_by_model_name'] && field['inverse_fname_by_model_name'][comodelName];
            if (!inverseFieldName) {
                // field has no inverse, skip it.
                continue;
            }
            const relatedRecordIds = Array.isArray(record[fname]) ? record[fname] : [record[fname]];
            // we only want to set a value for comodel inverse field if the model field has a value.
            if (record[fname]) {
                for (const relatedRecordId of relatedRecordIds) {
                    let inverseFieldNewValue = record.id;
                    const relatedRecord = this.data[comodelName].records.find(record => record.id === relatedRecordId);
                    const relatedFieldValue = relatedRecord && relatedRecord[inverseFieldName];
                    if (
                        relatedFieldValue === undefined ||
                        relatedFieldValue === record.id ||
                        field.type !== 'one2many' && relatedFieldValue.includes(record.id)
                    ) {
                        // related record does not exist or the related value is already up to date.
                        continue;
                    }
                    if (Array.isArray(relatedFieldValue)) {
                        inverseFieldNewValue = [...relatedFieldValue, record.id];
                    }
                    this._writeRecord(comodelName, { [inverseFieldName]: inverseFieldNewValue }, relatedRecordId);
                }
            } else if (field.type === 'many2one_reference') {
                // we need to clean the many2one_field as well.
                const comodel_inverse_field = this.data[comodelName].fields[inverseFieldName];
                const model_many2one_field = comodel_inverse_field['inverse_fname_by_model_name'][modelName];
                this._writeRecord(modelName, { [model_many2one_field]: false }, record.id);
            }
            // it's an update, get the records that were originally referenced but are not
            // anymore and update their relational fields.
            if (originalRecord) {
                const originalRecordIds = Array.isArray(originalRecord[fname]) ? originalRecord[fname] : [originalRecord[fname]];
                // search read returns [id, name], let's ensure the removedRecordIds are integers.
                const removedRecordIds = originalRecordIds.filter(recordId => Number.isInteger(recordId) && !relatedRecordIds.includes(recordId));
                for (const removedRecordId of removedRecordIds) {
                    const removedRecord = this.data[comodelName].records.find(record => record.id === removedRecordId);
                    if (!removedRecord) {
                        continue;
                    }
                    let inverseFieldNewValue = false;
                    if (Array.isArray(removedRecord[inverseFieldName])) {
                        inverseFieldNewValue = removedRecord[inverseFieldName].filter(id => id !== record.id);
                    }
                    this._writeRecord(comodelName, { [inverseFieldName]: inverseFieldNewValue }, removedRecordId);
                }
            }
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
     * @param {Object} [params={}]
     * @param {boolean} [params.ensureIntegrity=true] writing non-existing id
     *  in many2one field will throw if this param is true
     */
    _writeRecord: function (model, values, id, { ensureIntegrity = true } = {}) {
        var self = this;
        var record = _.findWhere(this.data[model].records, {id: id});
        for (var field_changed in values) {
            var field = this.data[model].fields[field_changed];
            var value = values[field_changed];
            if (!field) {
                throw Error(`Mock: Can't write value "${JSON.stringify(value)}" on field "${field_changed}" on record "${model},${id}" (field is undefined)`);
            }
            if (_.contains(['one2many', 'many2many'], field.type)) {
                var ids = _.clone(record[field_changed]) || [];

                if (
                    Array.isArray(value) &&
                    value.reduce((hasOnlyInt, val) => hasOnlyInt && Number.isInteger(val), true)
                ) {
                    // fallback to command 6 when given a simple list of ids
                    value = [[6, 0, value]];
                } else if (value === false) {
                    // delete all command
                    value = [[5]];
                }
                // convert commands
                for (const command of value || []) {
                    if (command[0] === 0) { // CREATE
                        const inverseData = command[2]; // write in place instead of copy, because some tests rely on the object given being updated
                        const inverseFieldName = field.inverse_fname_by_model_name && field.inverse_fname_by_model_name[field.relation];
                        if (inverseFieldName) {
                            inverseData[inverseFieldName] = id;
                        }
                        const newId = self._mockCreate(field.relation, inverseData);
                        ids.push(newId);
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
                        // copy array to avoid leak by reference (eg. of default data)
                        ids = [...command[2]];
                    } else {
                        throw Error(`Command "${JSON.stringify(value)}" not supported by the MockServer on field "${field_changed}" on record "${model},${id}"`);
                    }
                }
                record[field_changed] = ids;
            } else if (field.type === 'many2one') {
                if (value) {
                    var relatedRecord = _.findWhere(this.data[field.relation].records, {
                        id: value
                    });
                    if (!relatedRecord && ensureIntegrity) {
                        throw Error(`Wrong id "${JSON.stringify(value)}" for a many2one on field "${field_changed}" on record "${model},${id}"`);
                    }
                    record[field_changed] = value;
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
