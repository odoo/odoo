/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { Domain } from "@web/core/domain";
import { evaluateExpr } from "@web/core/py_js/py";
import { registry } from "@web/core/registry";
import * as utils from "@web/core/utils/arrays";
import { makeFakeRPCService, makeMockFetch } from "./mock_services";
import { patchWithCleanup } from "./utils";

const { DateTime } = luxon;
const serviceRegistry = registry.category("services");

// -----------------------------------------------------------------------------
// Utils
// -----------------------------------------------------------------------------

function traverseElementTree(tree, cb) {
    if (cb(tree)) {
        Array.from(tree.children).forEach((c) => traverseElementTree(c, cb));
    }
}

// -----------------------------------------------------------------------------
// MockServer
// -----------------------------------------------------------------------------

export class MockServer {
    constructor(data, options = {}) {
        this.models = data.models || {};
        this.actions = data.actions || {};
        this.menus = data.menus || null;
        this.archs = data.views || {};
        this.debug = options.debug || false;
        Object.entries(this.models).forEach(([modelName, model]) => {
            if (!("id" in model.fields)) {
                model.fields.id = { string: "ID", type: "integer" };
            }
            if (!("display_name" in model.fields)) {
                model.fields.display_name = { string: "Display Name", type: "char" };
            }
            if (!("__last_update" in model.fields)) {
                model.fields.__last_update = { string: "Last Modified on", type: "datetime" };
            }
            if (!("name" in model.fields)) {
                model.fields.name = { string: "Name", type: "char", default: "name" };
            }
            model.records = model.records || [];
            for (var i = 0; i < model.records.length; i++) {
                const values = model.records[i];
                // add potentially missing id
                const id = values.id === undefined ? this.getUnusedID(modelName) : values.id;
                // create a clean object, initial values are passed to write
                model.records[i] = { id };
                // ensure initial data goes through proper conversion (x2m, ...)
                this.applyDefaults(model, values);
                this.writeRecord(modelName, values, id, { ensureIntegrity: false });
            }
            model.onchanges = model.onchanges || {};
            model.methods = model.methods || {};
        });
    }

    /**
     * Simulate a complete RPC call. This is the main method for this class.
     *
     * This method also log incoming and outgoing data, and stringify/parse data
     * to simulate a barrier between the server and the client. It also simulate
     * server errors.
     */
    async performRPC(route, args) {
        args = JSON.parse(JSON.stringify(args));
        if (this.debug) {
            console.log("%c[rpc] request " + route, "color: blue; font-weight: bold;", args);
            args = JSON.parse(JSON.stringify(args));
        }
        let result;
        // try {
        result = await this._performRPC(route, args);
        // } catch {
        //   const message = result && result.message;
        //   const event = result && result.event;
        //   const errorString = JSON.stringify(message || false);
        //   console.warn(
        //     "%c[rpc] response (error) " + route,
        //     "color: orange; font-weight: bold;",
        //     JSON.parse(errorString)
        //   );
        //   return Promise.reject({ message: errorString, event });
        // }
        const resultString = JSON.stringify(result || false);
        if (this.debug) {
            console.log(
                "%c[rpc] response" + route,
                "color: blue; font-weight: bold;",
                JSON.parse(resultString)
            );
        }
        return JSON.parse(resultString);
        // TODO?
        // var abort = def.abort || def.reject;
        // if (abort) {
        //     abort = abort.bind(def);
        // } else {
        //     abort = function () {
        //         throw new Error("Can't abort this request");
        //     };
        // }
        // def.abort = abort;
    }

    fieldsViewGet(modelName, args, kwargs) {
        if (!(modelName in this.models)) {
            throw new Error(`Model ${modelName} was not defined in mock server data`);
        }
        // find the arch
        let [viewId, viewType] = args;
        if (!viewId) {
            const contextKey = (viewType === "list" ? "tree" : viewType) + "_view_ref";
            if (contextKey in kwargs.context) {
                viewId = kwargs.context[contextKey];
            }
        }
        const key = [modelName, viewId, viewType].join(",");
        let arch = this.archs[key];
        if (!arch) {
            const genericViewKey = Object.keys(this.archs).find((fullKey) => {
                const [_model, _viewID, _viewType] = fullKey.split(",");
                return _model === modelName && _viewType === viewType;
            });
            if (genericViewKey) {
                arch = this.archs[genericViewKey];
                viewId = parseInt(genericViewKey.split(",")[1], 10) || false;
            }
        }
        if (!arch) {
            throw new Error("No arch found for key " + key);
        }
        // generate a field_view_get result
        const fields = Object.assign({}, this.models[modelName].fields);
        // var viewOptions = params.viewOptions || {};
        const fvg = this._fieldsViewGet({ arch, modelName, fields, context: kwargs.context || {} });
        if (kwargs.options.toolbar) {
            fvg.toolbar = this.models[modelName].toolbar || {};
        }
        if (viewId) {
            fvg.view_id = viewId;
            fvg.name = key;
        }
        return fvg;
    }

    _fieldsViewGet(params) {
        let processedNodes = params.processedNodes || [];
        const { arch, context, fields, modelName } = params;
        function isNodeProcessed(node) {
            return processedNodes.findIndex((n) => n.isSameNode(node)) > -1;
        }
        const modifiersNames = ["invisible", "readonly", "required"];
        const onchanges = this.models[modelName].onchanges || {};
        const fieldNodes = {};
        const groupbyNodes = {};
        let doc;
        if (typeof arch === "string") {
            const domParser = new DOMParser();
            doc = domParser.parseFromString(arch, "text/xml").documentElement;
        } else {
            doc = arch;
        }
        const inTreeView = doc.tagName === "tree";
        // mock _postprocess_access_rights
        const isBaseModel = !context.base_model_name || modelName === context.base_model_name;
        const views = ["kanban", "tree", "form", "gantt", "activity"];
        if (isBaseModel && views.indexOf(doc.tagName) !== -1) {
            for (const action of ["create", "delete", "edit", "write"]) {
                if (!doc.getAttribute(action) && action in context && !context[action]) {
                    doc.setAttribute(action, "false");
                }
            }
        }

        traverseElementTree(doc, (node) => {
            if (node.nodeType === Node.TEXT_NODE) {
                return false;
            }
            const modifiers = {};
            const isField = node.tagName === "field";
            const isGroupby = node.tagName === "groupby";
            if (isField) {
                const fieldName = node.getAttribute("name");
                fieldNodes[fieldName] = node;
                // 'transfer_field_to_modifiers' simulation
                const field = fields[fieldName];
                if (!field) {
                    throw new Error("Field " + fieldName + " does not exist");
                }
                const defaultValues = {};
                const stateExceptions = {}; // what is this ?
                modifiersNames.forEach((attr) => {
                    stateExceptions[attr] = [];
                    defaultValues[attr] = !!field[attr];
                });
                // LPE: what is this ?
                /*                _.each(field.states || {}, function (modifs, state) {
                            _.each(modifs, function (modif) {
                                if (defaultValues[modif[0]] !== modif[1]) {
                                    stateExceptions[modif[0]].append(state);
                                }
                            });
                        });*/
                Object.entries(defaultValues).forEach(([attr, defaultValue]) => {
                    if (stateExceptions[attr].length) {
                        modifiers[attr] = [
                            ["state", defaultValue ? "not in" : "in", stateExceptions[attr]],
                        ];
                    } else {
                        modifiers[attr] = defaultValue;
                    }
                });
            } else if (isGroupby && !isNodeProcessed(node)) {
                const groupbyName = node.getAttribute("name");
                fieldNodes[groupbyName] = node;
                groupbyNodes[groupbyName] = node;
            }
            // 'transfer_node_to_modifiers' simulation
            let attrs = node.getAttribute("attrs");
            if (attrs) {
                attrs = evaluateExpr(attrs);
                Object.assign(modifiers, attrs);
            }
            const states = node.getAttribute("states");
            if (states) {
                if (!modifiers.invisible) {
                    modifiers.invisible = [];
                }
                modifiers.invisible.push(["state", "not in", states.split(",")]);
            }
            const inListHeader = inTreeView && node.closest("header");
            modifiersNames.forEach((attr) => {
                const mod = node.getAttribute(attr);
                if (mod) {
                    // TODO
                    // const pyevalContext = window.py.dict.fromJSON(context || {});
                    // var v = pyUtils.py_eval(mod, {context: pyevalContext}) ? true : false;
                    console.info("MockServer: naive parse of modifier value in", QUnit.config.current.testName);
                    const v = JSON.parse(mod);
                    if (inTreeView && !inListHeader && attr === "invisible") {
                        modifiers.column_invisible = v;
                    } else if (v || !(attr in modifiers) || !Array.isArray(modifiers[attr])) {
                        modifiers[attr] = v;
                    }
                }
            });
            modifiersNames.forEach((attr) => {
                if (
                    attr in modifiers &&
                    (!!modifiers[attr] === false ||
                        (Array.isArray(modifiers[attr]) && !modifiers[attr].length))
                ) {
                    delete modifiers[attr];
                }
            });
            if (Object.keys(modifiers).length) {
                node.setAttribute("modifiers", JSON.stringify(modifiers));
            }
            if (isGroupby && !isNodeProcessed(node)) {
                return false;
            }
            return !isField;
        });
        let relModel, relFields;
        Object.entries(fieldNodes).forEach(([name, node]) => {
            const field = fields[name];
            if (field.type === "many2one" || field.type === "many2many") {
                const canCreate = node.getAttribute("can_create");
                node.setAttribute("can_create", canCreate || "true");
                const canWrite = node.getAttribute("can_write");
                node.setAttribute("can_write", canWrite || "true");
            }
            if (field.type === "one2many" || field.type === "many2many") {
                field.views = {};
                Array.from(node.children).forEach((children) => {
                    if (children.tagName) {
                        // skip text nodes
                        relModel = field.relation;
                        relFields = Object.assign({}, this.models[relModel].fields);
                        field.views[children.tagName] = this._fieldsViewGet({
                            arch: children,
                            modelName: relModel,
                            fields: relFields,
                            context: Object.assign({}, context, { base_model_name: modelName }),
                            processedNodes,
                        });
                    }
                });
            }
            // add onchanges
            if (name in onchanges) {
                node.setAttribute("on_change", "1");
            }
        });
        Object.entries(groupbyNodes).forEach(([name, node]) => {
            const field = fields[name];
            if (field.type !== "many2one") {
                throw new Error("groupby can only target many2one");
            }
            field.views = {};
            relModel = field.relation;
            relFields = Object.assign({}, this.models[relModel].fields);
            processedNodes.push(node);
            // postprocess simulation
            field.views.groupby = this._fieldsViewGet({
                arch: node,
                modelName: relModel,
                fields: relFields,
                context,
                processedNodes,
            });
            while (node.firstChild) {
                node.removeChild(node.firstChild);
            }
        });
        const xmlSerializer = new XMLSerializer();
        const processedArch = xmlSerializer.serializeToString(doc);
        const fieldsInView = {};
        Object.entries(fields).forEach(([fname, field]) => {
            if (fname in fieldNodes) {
                fieldsInView[fname] = field;
            }
        });
        return {
            arch: processedArch,
            fields: fieldsInView,
            model: modelName,
            type: doc.tagName === "tree" ? "list" : doc.tagName,
        };
    }

    /**
     * Converts an Object representing a record to actual return Object of the
     * python `onchange` method.
     * Specifically, it applies `name_get` on many2one's and transforms raw id
     * list in orm command lists for x2many's.
     * For x2m fields that add or update records (ORM commands 0 and 1), it is
     * recursive.
     *
     * @param {string} model: the model's name
     * @param {Object} values: an object representing a record
     * @returns {Object}
     */
    convertToOnChange(modelName, values) {
        Object.entries(values).forEach(([fname, val]) => {
            const field = this.models[modelName].fields[fname];
            if (field.type === "many2one" && typeof val === "number") {
                // implicit name_get
                const m2oRecord = this.models[field.relation].records.find((r) => r.id === val);
                values[fname] = [val, m2oRecord.display_name];
            } else if (field.type === "one2many" || field.type === "many2many") {
                // TESTS ONLY
                // one2many_ids = [1,2,3] is a simpler way to express it than orm commands
                const isCommandList = Array.isArray(val) && Array.isArray(val[0]);
                if (!isCommandList) {
                    values[fname] = [[6, false, val]];
                } else {
                    val.forEach((cmd) => {
                        if (cmd[0] === 0 || cmd[0] === 1) {
                            cmd[2] = this.convertToOnChange(field.relation, cmd[2]);
                        }
                    });
                }
            }
        });
        return values;
    }

    _performRPC(route, args) {
        switch (route) {
            case "/web/webclient/load_menus":
                return Promise.resolve(this.mockLoadMenus());
            case "/web/action/load":
                return Promise.resolve(this.mockLoadAction(args));
            case "/web/dataset/search_read":
                return Promise.resolve(this.mockSearchReadController(args));
            case "/web/dataset/search":
                return Promise.resolve(this.mockSearchController(args));
        }
        if (
            route.indexOf("/web/image") >= 0 ||
            [".png", ".jpg"].includes(route.substr(route.length - 4))
        ) {
            return Promise.resolve();
        }
        switch (args.method) {
            case "create":
                return Promise.resolve(this.mockCreate(args.model, args.args[0]));
            case "fields_get":
                return Promise.resolve(this.mockFieldsGet(args.model));
            case "load_views":
                return Promise.resolve(this.mockLoadViews(args.model, args.kwargs));
            case "name_create":
                return Promise.resolve(this.mockNameCreate(args.model, args.args[0]));
            case "name_get":
                return Promise.resolve(this.mockNameGet(args.model, args.args));
            case "name_search":
                return Promise.resolve(this.mockNameSearch(args.model, args.args, args.kwargs));
            case "onchange":
                return Promise.resolve(this.mockOnchange(args.model, args.args, args.kwargs));
            case "read":
                return Promise.resolve(this.mockRead(args.model, args.args));
            case "search":
                return Promise.resolve(this.mockSearch(args.model, args.args, args.kwargs));
            case "search_count":
                return Promise.resolve(this.mockSearchCount(args.model, args.args, args.kwargs));
            case "search_read":
                return Promise.resolve(this.mockSearchRead(args.model, args.args, args.kwargs));
            case "search_panel_select_range":
                return Promise.resolve(
                    this.mockSearchPanelSelectRange(args.model, args.args, args.kwargs)
                );
            case "search_panel_select_multi_range":
                return Promise.resolve(
                    this.mockSearchPanelSelectMultiRange(args.model, args.args, args.kwargs)
                );
            case "web_search_read":
                return Promise.resolve(this.mockWebSearchRead(args.model, args.args, args.kwargs));
            case "read_group":
                return Promise.resolve(this.mockReadGroup(args.model, args.kwargs));
            case "web_read_group":
                return Promise.resolve(this.mockWebReadGroup(args.model, args.kwargs));
            case "write":
                return Promise.resolve(this.mockWrite(args.model, args.args));
        }
        const model = this.models[args.model];
        const method = model && model.methods[args.method];
        if (method) {
            return Promise.resolve(method(args.model, args.args, args.kwargs));
        }
        throw new Error(`Unimplemented route: ${route}`);
    }

    mockCreate(modelName, values) {
        if ("id" in values) {
            throw new Error("Cannot create a record with a predefinite id");
        }
        const model = this.models[modelName];
        const id = this.getUnusedID(modelName);
        const record = { id };
        model.records.push(record);
        this.applyDefaults(model, values);
        this.writeRecord(modelName, values, id);
        return id;
    }

    /**
     * @param {string} modelName
     * @param {array[]} args a list with a list of fields in the first position
     * @param {Object} [kwargs={}]
     * @param {Object} [kwargs.context] the context to eventually read default
     *   values
     * @returns {Object}
     */
    mockDefaultGet(modelName, args, kwargs = {}) {
        const fields = args[0];
        const model = this.models[modelName];
        const result = {};
        for (const fieldName of fields) {
            const key = "default_" + fieldName;
            if (kwargs.context && key in kwargs.context) {
                result[fieldName] = kwargs.context[key];
                continue;
            }
            const field = model.fields[fieldName];
            if ("default" in field) {
                result[fieldName] = field.default;
                continue;
            }
        }
        for (const fieldName in result) {
            const field = model.fields[fieldName];
            if (field.type === "many2one") {
                const recordExists = this.models[field.relation].records.some(
                    (r) => r.id === result[fieldName]
                );
                if (!recordExists) {
                    delete result[fieldName];
                }
            }
        }
        return result;
    }

    mockFieldsGet(modelName) {
        return this.models[modelName].fields;
    }

    mockLoadAction(kwargs) {
        const action = this.actions[kwargs.action_id];
        if (!action) {
            // when the action doesn't exist, the real server doesn't crash, it
            // simply returns false
            console.warn(`No action found for ID ${kwargs.action_id} during test ${QUnit.config.current.testName}`);
        }
        return action || false;
    }

    mockLoadMenus() {
        let menus = this.menus;
        if (!menus) {
            menus = {
                root: { id: "root", children: [1], name: "root", appID: "root" },
                1: { id: 1, children: [], name: "App0", appID: 1 },
            };
        }
        return menus;
    }

    mockLoadViews(modelName, kwargs) {
        const fieldsViews = {};
        kwargs.views.forEach(([viewId, viewType]) => {
            fieldsViews[viewType] = this.fieldsViewGet(modelName, [viewId, viewType], kwargs);
        });
        const result = {
            fields: this.mockFieldsGet(modelName),
            fields_views: fieldsViews,
        };
        if (kwargs.options.load_filters) {
            result.filters = this.models[modelName].filters || [];
        }
        return result;
    }

    /**
     * Simulate a 'name_create' operation
     *
     * @private
     * @param {string} model
     * @param {string} name
     * @returns {Array} a couple [id, name]
     */
    mockNameCreate(modelName, name) {
        const values = {
            name: name,
            display_name: name,
        };
        const id = this.mockCreate(modelName, values);
        return [id, name];
    }

    /**
     * Simulate a 'name_get' operation
     *
     * @private
     * @param {string} model
     * @param {Array} args
     * @returns {Array[]} a list of [id, display_name]
     */
    mockNameGet(model, args) {
        var ids = args[0];
        if (!args.length) {
            throw new Error("name_get: expected one argument");
        } else if (!ids) {
            return [];
        }
        if (!Array.isArray(ids)) {
            ids = [ids];
        }
        var records = this.models[model].records;
        var names = ids.map((id) =>
            id ? [id, records.find((r) => r.id === id).display_name] : [null, "False"]
        );
        return names;
    }

    /**
     * Simulate a 'name_search' operation.
     *
     * @param {string} model
     * @param {Array} args
     * @param {string} args[0]
     * @param {Array} args[1], search domain
     * @param {Object} kwargs
     * @param {number} [kwargs.limit=100] server-side default limit
     * @returns {Array[]} a list of [id, display_name]
     */
    mockNameSearch(model, args, kwargs) {
        const str = args && typeof args[0] === "string" ? args[0] : kwargs.name;
        const limit = kwargs.limit || 100;
        const domain = (args && args[1]) || kwargs.args || [];
        let { records } = this.models[model];
        const result = [];
        for (const r of records) {
            const isInDomain = this.evaluateDomain(domain, r);
            if (isInDomain && (!str.length || r.display_name.includes(str))) {
                result.push([r.id, r.display_name]);
            }
        }
        return result.slice(0, limit);
    }

    mockOnchange(modelName, args, kwargs) {
        const currentData = args[1];
        const onChangeSpec = args[3];
        let fields = args[2] ? (Array.isArray(args[2]) ? args[2] : [args[2]]) : [];
        const onchanges = this.models[modelName].onchanges || {};
        const firstOnChange = !fields.length;
        const onchangeVals = {};
        let defaultVals = undefined;
        let nullValues;
        if (firstOnChange) {
            const fieldsFromView = Object.keys(onChangeSpec).reduce((acc, fname) => {
                fname = fname.split(".", 1)[0];
                if (!acc.includes(fname)) {
                    acc.push(fname);
                }
                return acc;
            }, []);
            const defaultingFields = fieldsFromView.filter((fname) => !(fname in currentData));
            defaultVals = this.mockDefaultGet(modelName, [defaultingFields], kwargs);
            // It is the new semantics: no field in arguments means we are in
            // a default_get + onchange situation
            fields = fieldsFromView;
            nullValues = {};
            fields
                .filter((fName) => !Object.keys(defaultVals).includes(fName))
                .forEach((fName) => {
                    nullValues[fName] = false;
                });
        }
        Object.assign(currentData, defaultVals);
        fields.forEach((field) => {
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
            value: this.convertToOnChange(modelName, Object.assign({}, defaultVals, onchangeVals)),
        };
    }

    mockRead(modelName, args) {
        const model = this.models[modelName];
        let fields;
        if (args[1] && args[1].length) {
            fields = [...new Set(args[1].concat(["id"]))];
        } else {
            fields = Object.keys(model.fields);
        }
        const ids = Array.isArray(args[0]) ? args[0] : [args[0]];
        const records = ids.reduce((records, id) => {
            if (!id) {
                throw new Error(
                    "mock read: falsy value given as id, would result in an access error in actual server !"
                );
            }
            const record = model.records.find((r) => r.id === id);
            return record ? records.concat(record) : records;
        }, []);
        return records.map((record) => {
            const result = { id: record.id };
            for (const fieldName of fields) {
                const field = model.fields[fieldName];
                if (!field) {
                    continue; // the field doens't exist on the model, so skip it
                }
                if (["float", "integer", "monetary"].includes(field.type)) {
                    // read should return 0 for unset numeric fields
                    result[fieldName] = record[fieldName] || 0;
                } else if (field.type === "many2one") {
                    const CoModel = this.models[field.relation];
                    const relRecord = CoModel.records.find((r) => r.id === record[fieldName]);
                    if (relRecord) {
                        result[fieldName] = [record[fieldName], relRecord.display_name];
                    } else {
                        result[fieldName] = false;
                    }
                } else if (field.type === "one2many" || field.type === "many2many") {
                    result[fieldName] = record[fieldName] || [];
                } else {
                    result[fieldName] = record[fieldName] || false;
                }
            }
            return result;
        });
    }

    mockReadGroup(modelName, kwargs) {
        if (!("lazy" in kwargs)) {
            kwargs.lazy = true;
        }
        const fields = this.models[modelName].fields;
        const records = this.getRecords(modelName, kwargs.domain);
        let groupBy = [];
        if (kwargs.groupby.length) {
            groupBy = kwargs.lazy ? [kwargs.groupby[0]] : kwargs.groupby;
        }
        const groupByFieldNames = groupBy.map((groupByField) => {
            return groupByField.split(":")[0];
        });
        let aggregatedFields = [];
        // if no fields have been given, the server picks all stored fields
        if (kwargs.fields.length === 0) {
            aggregatedFields = Object.keys(this.models[modelName].fields).filter(
                (fieldName) => !groupByFieldNames.includes(fieldName)
            );
        } else {
            kwargs.fields.forEach((field) => {
                var split = field.split(":");
                var fieldName = split[0];
                if (!fields[fieldName]) {
                    return;
                }
                if (groupByFieldNames.includes(fieldName)) {
                    // grouped fields are not aggregated
                    return;
                }
                if (
                    fields[fieldName] &&
                    fields[fieldName].type === "many2one" &&
                    split[1] !== "count_distinct"
                ) {
                    return;
                }
                aggregatedFields.push(fieldName);
            });
        }
        function aggregateFields(group, records) {
            let type;
            for (let i = 0; i < aggregatedFields.length; i++) {
                type = fields[aggregatedFields[i]].type;
                if (type === "float" || type === "integer") {
                    group[aggregatedFields[i]] = null;
                    for (let j = 0; j < records.length; j++) {
                        const value = group[aggregatedFields[i]] || 0;
                        group[aggregatedFields[i]] = value + records[j][aggregatedFields[i]];
                    }
                }
                if (type === "many2one") {
                    const ids = records.map((record) => record[aggregatedFields[i]]);
                    group[aggregatedFields[i]] = [...new Set(ids)].length || null;
                }
            }
        }
        function formatValue(groupByField, val) {
            let [fieldName, aggregateFunction] = groupByField.split(":");
            aggregateFunction = aggregateFunction || "month";
            if (fields[fieldName].type === "date") {
                // what about datetime?
                if (!val) {
                    return false;
                }
                const date = DateTime.fromISO(val);
                if (aggregateFunction === "day") {
                    return date.toFormat("yyyy-MM-dd");
                } else if (aggregateFunction === "week") {
                    return `W${date.toFormat("W yyyy")}`;
                } else if (aggregateFunction === "quarter") {
                    return `Q${date.toFormat("q yyyy")}`;
                } else if (aggregateFunction === "year") {
                    return date.toFormat("yyyy");
                } else {
                    return date.toFormat("MMMM yyyy");
                }
            } else {
                return val instanceof Array ? val[0] : val || false;
            }
        }
        function groupByFunction(record) {
            let value = "";
            groupBy.forEach((groupByField) => {
                value = (value ? value + "," : value) + groupByField + "#";
                const fieldName = groupByField.split(":")[0];
                if (fields[fieldName].type === "date") {
                    value += formatValue(groupByField, record[fieldName]);
                } else {
                    value += JSON.stringify(record[groupByField]);
                }
            });
            return value;
        }
        if (!groupBy.length) {
            const group = { __count: records.length };
            aggregateFields(group, records);
            return [group];
        }
        const groups = utils.groupBy(records, groupByFunction);
        let result = Object.values(groups).map((records) => {
            const res = {
                __domain: kwargs.domain || [],
            };
            groupBy.forEach((groupByField) => {
                const fieldName = groupByField.split(":")[0];
                const val = formatValue(groupByField, records[0][fieldName]);
                const field = fields[fieldName];
                if (field.type === "many2one" && !Array.isArray(val)) {
                    const relRecord = this.models[field.relation].records.find((r) => r.id === val);
                    if (relRecord) {
                        res[groupByField] = [val, relRecord.display_name];
                    } else {
                        res[groupByField] = false;
                    }
                } else {
                    res[groupByField] = val;
                }
                if (field.type === "date" && val) {
                    console.info("Mock Server: read group not fully implemented (moment stuff) in", QUnit.config.current.testName);
                    // const aggregateFunction = groupByField.split(':')[1];
                    // let startDate;
                    // let endDate;
                    // if (aggregateFunction === 'day') {
                    //     startDate = moment(val, 'YYYY-MM-DD');
                    //     endDate = startDate.clone().add(1, 'days');
                    // } else if (aggregateFunction === 'week') {
                    //     startDate = moment(val, 'ww YYYY');
                    //     endDate = startDate.clone().add(1, 'weeks');
                    // } else if (aggregateFunction === 'year') {
                    //     startDate = moment(val, 'Y');
                    //     endDate = startDate.clone().add(1, 'years');
                    // } else {
                    //     startDate = moment(val, 'MMMM YYYY');
                    //     endDate = startDate.clone().add(1, 'months');
                    // }
                    // res.__domain = [[fieldName, '>=', startDate.format('YYYY-MM-DD')], [fieldName, '<', endDate.format('YYYY-MM-DD')]].concat(res.__domain);
                } else {
                    res.__domain = Domain.combine(
                        [[[fieldName, "=", val]], res.__domain],
                        "AND"
                    ).toList();
                }
            });
            // compute count key to match dumb server logic...
            let countKey;
            if (kwargs.lazy) {
                countKey = groupBy[0].split(":")[0] + "_count";
            } else {
                countKey = "__count";
            }
            res[countKey] = records.length;
            aggregateFields(res, records);
            return res;
        });
        if (kwargs.orderby) {
            // only consider first sorting level
            kwargs.orderby = kwargs.orderby.split(",")[0];
            const fieldName = kwargs.orderby.split(" ")[0];
            const order = kwargs.orderby.split(" ")[1];
            result = this.sortByField(result, modelName, fieldName, order);
        }
        if (kwargs.limit) {
            const offset = kwargs.offset || 0;
            result = result.slice(offset, kwargs.limit + offset);
        }
        return result;
    }

    mockWebReadGroup(modelName, kwargs) {
        const groups = this.mockReadGroup(modelName, kwargs);
        if (kwargs.expand && kwargs.groupby.length === 1) {
            groups.forEach((group) => {
                group.__data = this.mockSearchReadController({
                    domain: group.__domain,
                    model: modelName,
                    fields: kwargs.fields,
                    limit: kwargs.expand_limit,
                    sort: kwargs.expand_orderby,
                });
            });
        }
        const allGroups = this.mockReadGroup(modelName, {
            domain: kwargs.domain,
            fields: ["display_name"],
            groupby: kwargs.groupby,
            lazy: kwargs.lazy,
        });
        return {
            groups: groups,
            length: allGroups.length,
        };
    }

    mockSearch(modelName, args, kwargs) {
        const result = this.mockSearchController({
            model: modelName,
            domain: kwargs.domain || args[0],
            fields: kwargs.fields || args[1],
            offset: kwargs.offset || args[2],
            limit: kwargs.limit || args[3],
            sort: kwargs.order || args[4],
            context: kwargs.context,
        });
        return result.records;
    }

    /**
     * Simulate a 'search_count' operation
     *
     * @private
     * @param {string} model
     * @param {Array} args
     * @returns {integer}
     */
    mockSearchCount(model, args) {
        return this.getRecords(model, args[0]).length;
    }

    mockSearchRead(modelName, args, kwargs) {
        const result = this.mockSearchReadController({
            model: modelName,
            domain: kwargs.domain || args[0],
            fields: kwargs.fields || args[1],
            offset: kwargs.offset || args[2],
            limit: kwargs.limit || args[3],
            sort: kwargs.order || args[4],
            context: kwargs.context,
        });
        return result.records;
    }

    mockWebSearchRead(modelName, args, kwargs) {
        const result = this.mockSearchReadController({
            model: modelName,
            domain: kwargs.domain || args[0],
            fields: kwargs.fields || args[1],
            offset: kwargs.offset || args[2],
            limit: kwargs.limit || args[3],
            sort: kwargs.order || args[4],
            context: kwargs.context,
        });
        return result;
    }

    mockSearchController(params) {
        const model = this.models[params.model];
        let fieldNames = params.fields;
        const offset = params.offset || 0;
        if (!fieldNames || !fieldNames.length) {
            fieldNames = Object.keys(model.fields);
        }
        fieldNames = [...new Set(fieldNames.concat(["id"]))];
        let records = this.getRecords(params.model, params.domain || []);
        if (params.sort) {
            // warning: only consider first level of sort
            params.sort = params.sort.split(",")[0];
            const fieldName = params.sort.split(" ")[0];
            const order = params.sort.split(" ")[1];
            records = this.sortByField(records, params.model, fieldName, order);
        }
        const nbRecords = records.length;
        records = records.slice(offset, params.limit ? offset + params.limit : nbRecords);
        return {
            fieldNames,
            length: nbRecords,
            records,
        };
    }

    mockSearchReadController(params) {
        const { fieldNames, length, records } = this.mockSearchController(params);
        return {
            length,
            records: this.mockRead(params.model, [records.map((r) => r.id), fieldNames]),
        };
    }

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
    mockSearchPanelDomainImage(model, fieldName, domain, setCount = false, limit = false) {
        const field = this.models[model].fields[fieldName];
        let groupIdName;
        if (field.type === "many2one") {
            groupIdName = (value) => value || [false, undefined];
            // mockReadGroup does not take care of the condition [fieldName, '!=', false]
            // in the domain defined below !!!
        } else if (field.type === "selection") {
            const selection = {};
            for (const [value, label] of this.models[model].fields[fieldName].selection) {
                selection[value] = label;
            }
            groupIdName = (value) => [value, selection[value]];
        }
        domain = Domain.combine([domain, [[fieldName, "!=", false]]]).toList();
        const groups = this.mockReadGroup(model, {
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
                values.__count = group[fieldName + "_count"];
            }
            domainImage.set(id, values);
        }
        return domainImage;
    }

    /**
     * Simulates a call to the server '_search_panel_field_image' method.
     *
     * @private
     * @param {string} model
     * @param {string} fieldName
     * @param {Object} kwargs
     * @see _mockSearchPanelDomainImage()
     */
    mockSearchPanelFieldImage(model, fieldName, kwargs) {
        const enableCounters = kwargs.enable_counters;
        const onlyCounters = kwargs.only_counters;
        const extraDomain = kwargs.extra_domain || [];
        const normalizedExtra = new Domain(extraDomain).toList();
        const noExtra = JSON.stringify(normalizedExtra) === "[]";
        const modelDomain = kwargs.model_domain || [];
        const countDomain = Domain.combine([modelDomain, extraDomain]).toList();

        const limit = kwargs.limit;
        const setLimit = kwargs.set_limit;

        if (onlyCounters) {
            return this.mockSearchPanelDomainImage(model, fieldName, countDomain, true);
        }

        const modelDomainImage = this.mockSearchPanelDomainImage(
            model,
            fieldName,
            modelDomain,
            enableCounters && noExtra,
            setLimit && limit
        );
        if (enableCounters && !noExtra) {
            const countDomainImage = this.mockSearchPanelDomainImage(
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
    }

    /**
     * Simulates a call to the server '_search_panel_global_counters' method.
     *
     * @private
     * @param {Map} valuesRange
     * @param {(string|boolean)} parentName 'parent_id' or false
     */
    mockSearchPanelGlobalCounters(valuesRange, parentName) {
        const localCounters = [...valuesRange.keys()].map((id) => valuesRange.get(id).__count);
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
    }

    /**
     * Simulates a call to the server '_search_panel_sanitized_parent_hierarchy' method.
     *
     * @private
     * @param {Object[]} records
     * @param {(string|boolean)} parentName 'parent_id' or false
     * @param {number[]} ids
     * @returns {Object[]}
     */
    mockSearchPanelSanitizedParentHierarchy(records, parentName, ids) {
        const getParentId = (record) => record[parentName] && record[parentName][0];
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
        return records.filter((rec) => recordsToKeep[rec.id]);
    }

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
    mockSearchPanelSelectRange(model, [fieldName], kwargs) {
        const field = this.models[model].fields[fieldName];
        const supportedTypes = ["many2one", "selection"];
        if (!supportedTypes.includes(field.type)) {
            throw new Error(
                `Only types ${supportedTypes} are supported for category (found type ${field.type})`
            );
        }

        const modelDomain = kwargs.search_domain || [];
        const extraDomain = Domain.combine([
            kwargs.category_domain || [],
            kwargs.filter_domain || [],
        ]).toList();

        if (field.type === "selection") {
            const newKwargs = Object.assign({}, kwargs, {
                model_domain: modelDomain,
                extra_domain: extraDomain,
            });
            kwargs.model_domain = modelDomain;
            return {
                parent_field: false,
                values: this.mockSearchPanelSelectionRange(model, fieldName, newKwargs),
            };
        }

        const fieldNames = ["display_name"];
        let hierarchize = "hierarchize" in kwargs ? kwargs.hierarchize : true;
        let getParentId;
        let parentName = false;
        if (hierarchize && this.models[field.relation].fields.parent_id) {
            parentName = "parent_id"; // in tests, parent field is always 'parent_id'
            fieldNames.push(parentName);
            getParentId = (record) => record.parent_id && record.parent_id[0];
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
            domainImage = this.mockSearchPanelFieldImage(model, fieldName, newKwargs);
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
                const records = this.models[field.relation].records;
                const ancestorIds = new Set();
                for (const id of imageElementIds) {
                    let recordId = id;
                    let record;
                    while (recordId) {
                        ancestorIds.add(recordId);
                        record = records.find((rec) => rec.id === recordId);
                        recordId = record[parentName];
                    }
                }
                condition = ["id", "in", [...new Set(ancestorIds)]];
            } else {
                condition = ["id", "in", imageElementIds];
            }
            comodelDomain = Domain.combine([comodelDomain, [condition]]).toList();
        }
        let comodelRecords = this.mockSearchRead(field.relation, [comodelDomain, fieldNames], {
            limit,
        });

        if (hierarchize) {
            const ids = expand ? comodelRecords.map((rec) => rec.id) : imageElementIds;
            comodelRecords = this.mockSearchPanelSanitizedParentHierarchy(
                comodelRecords,
                parentName,
                ids
            );
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
                values.__count = domainImage.get(record.id)
                    ? domainImage.get(record.id).__count
                    : 0;
            }
            fieldRange.set(record.id, values);
        }

        if (hierarchize && enableCounters) {
            this.mockSearchPanelGlobalCounters(fieldRange, parentName);
        }

        return {
            parent_field: parentName,
            values: [...fieldRange.values()],
        };
    }

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
    mockSearchPanelSelectMultiRange(model, [fieldName], kwargs) {
        const field = this.models[model].fields[fieldName];
        const supportedTypes = ["many2one", "many2many", "selection"];
        if (!supportedTypes.includes(field.type)) {
            throw new Error(
                `Only types ${supportedTypes} are supported for filter (found type ${field.type})`
            );
        }
        let modelDomain = kwargs.search_domain || [];
        let extraDomain = Domain.combine([
            kwargs.category_domain || [],
            kwargs.filter_domain || [],
        ]).toList();
        if (field.type === "selection") {
            const newKwargs = Object.assign({}, kwargs, {
                model_domain: modelDomain,
                extra_domain: extraDomain,
            });
            return {
                values: this.mockSearchPanelSelectionRange(model, fieldName, newKwargs),
            };
        }
        const fieldNames = ["display_name"];
        const groupBy = kwargs.group_by;
        let groupIdName;
        if (groupBy) {
            const groupByField = this.models[field.relation].fields[groupBy];
            fieldNames.push(groupBy);
            if (groupByField.type === "many2one") {
                groupIdName = (value) => value || [false, "Not set"];
            } else if (groupByField.type === "selection") {
                const groupBySelection = Object.assign(
                    {},
                    this.models[field.relation].fields[groupBy].selection
                );
                groupBySelection[false] = "Not Set";
                groupIdName = (value) => [value, groupBySelection[value]];
            } else {
                groupIdName = (value) => (value ? [value, value] : [false, "Not set"]);
            }
        }
        let comodelDomain = kwargs.comodel_domain || [];
        const enableCounters = kwargs.enable_counters;
        const expand = kwargs.expand;
        const limit = kwargs.limit;
        if (field.type === "many2many") {
            const comodelRecords = this.mockSearchRead(
                field.relation,
                [comodelDomain, fieldNames],
                { limit }
            );
            if (expand && limit && comodelRecords.length === limit) {
                return { error_msg: "Too many items to display." };
            }

            const groupDomain = kwargs.group_domain;
            const fieldRange = [];
            for (const record of comodelRecords) {
                const values = {
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
                    const searchDomain = Domain.combine([
                        modelDomain,
                        [[fieldName, "in", record.id]],
                    ]).toList();
                    let localExtraDomain = extraDomain;
                    if (groupBy && groupDomain) {
                        localExtraDomain = Domain.combine([
                            localExtraDomain,
                            groupDomain[JSON.stringify(groupId)] || [],
                        ]).toList();
                    }
                    const searchCountDomain = Domain.combine([
                        searchDomain,
                        localExtraDomain,
                    ]).toList();
                    if (enableCounters) {
                        count = this.mockSearchCount(model, [searchCountDomain]);
                    }
                    if (!expand) {
                        if (enableCounters && JSON.stringify(localExtraDomain) === "[]") {
                            inImage = count;
                        } else {
                            inImage = this.mockSearch(model, [searchDomain], { limit: 1 }).length;
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

        if (field.type === "many2one") {
            let domainImage;
            if (enableCounters || !expand) {
                extraDomain = Domain.combine([extraDomain, kwargs.group_domain || []]).toList();
                modelDomain = Domain.combine([modelDomain, kwargs.group_domain || []]).toList();
                const newKwargs = Object.assign({}, kwargs, {
                    model_domain: modelDomain,
                    extra_domain: extraDomain,
                    only_counters: expand,
                    set_limit: limit && !(expand || groupBy || comodelDomain),
                });
                domainImage = this.mockSearchPanelFieldImage(model, fieldName, newKwargs);
            }
            if (!expand && !groupBy && !comodelDomain.length) {
                if (limit && domainImage.size === limit) {
                    return { error_msg: "Too many items to display." };
                }
                return { values: [...domainImage.values()] };
            }
            if (!expand) {
                const imageElementIds = [...domainImage.keys()].map(Number);
                comodelDomain = Domain.combine([
                    comodelDomain,
                    [["id", "in", imageElementIds]],
                ]).toList();
            }
            const comodelRecords = this.mockSearchRead(
                field.relation,
                [comodelDomain, fieldNames],
                { limit }
            );
            if (limit && comodelRecords.length === limit) {
                return { error_msg: "Too many items to display." };
            }

            const fieldRange = [];
            for (const record of comodelRecords) {
                const values = {
                    id: record.id,
                    display_name: record.display_name,
                };
                if (groupBy) {
                    const [groupId, groupName] = groupIdName(record[groupBy]);
                    values.group_id = groupId;
                    values.group_name = groupName;
                }
                if (enableCounters) {
                    values.__count = domainImage.get(record.id)
                        ? domainImage.get(record.id).__count
                        : 0;
                }
                fieldRange.push(values);
            }
            return { values: fieldRange };
        }
    }

    mockWrite(modelName, args) {
        args[0].forEach((id) => this.writeRecord(modelName, args[1], id));
        return true;
    }

    //////////////////////////////////////////////////////////////////////////////
    // Private
    //////////////////////////////////////////////////////////////////////////////
    evaluateDomain(domain, record) {
        return new Domain(domain).contains(record);
    }

    /**
     * Get all records from a model matching a domain.  The only difficulty is
     * that if we have an 'active' field, we implicitely add active = true in
     * the domain.
     */
    getRecords(modelName, domain, { active_test = true } = {}) {
        if (!Array.isArray(domain)) {
            throw new Error("MockServer._getRecords: given domain has to be an array.");
        }
        const model = this.models[modelName];
        // add ['active', '=', true] to the domain if 'active' is not yet present in domain
        if (active_test && "active" in model.fields) {
            const activeInDomain = domain.some((subDomain) => subDomain[0] === "active");
            if (!activeInDomain) {
                domain = domain.concat([["active", "=", true]]);
            }
        }
        let records = model.records;
        if (domain.length) {
            // 'child_of' operator isn't supported by domain.js, so we replace
            // in by the 'in' operator (with the ids of children)
            domain = domain.map((criterion) => {
                if (criterion[1] === "child_of") {
                    let oldLength = 0;
                    const childIDs = [criterion[2]];
                    while (childIDs.length > oldLength) {
                        oldLength = childIDs.length;
                        records.forEach((r) => {
                            if (childIDs.indexOf(r.parent_id) >= 0) {
                                childIDs.push(r.id);
                            }
                        });
                    }
                    criterion = [criterion[0], "in", childIDs];
                }
                return criterion;
            });
            records = records.filter((record) => this.evaluateDomain(domain, record));
        }
        return records;
    }

    sortByField(records, modelName, fieldName, order) {
        const field = this.models[modelName].fields[fieldName];
        records.sort((r1, r2) => {
            let v1 = r1[fieldName];
            let v2 = r2[fieldName];
            if (field.type === "many2one") {
                const coRecords = this.models[field.relation].records;
                if (this.models[field.relation].fields.sequence) {
                    // use sequence field of comodel to sort records
                    v1 = coRecords.find((r) => r.id === v1[0]).sequence;
                    v2 = coRecords.find((r) => r.id === v2[0]).sequence;
                } else {
                    // sort by id
                    v1 = v1[0];
                    v2 = v2[0];
                }
            }
            if (v1 < v2) {
                return order === "ASC" ? -1 : 1;
            }
            if (v1 > v2) {
                return order === "ASC" ? 1 : -1;
            }
            return 0;
        });
        return records;
    }

    writeRecord(modelName, values, id, { ensureIntegrity = true } = {}) {
        const model = this.models[modelName];
        const record = model.records.find((r) => r.id === id);
        for (const fieldName in values) {
            const field = model.fields[fieldName];
            let value = values[fieldName];
            if (!field) {
                throw Error(
                    `Mock: Can't write value "${JSON.stringify(
                        value
                    )}" on field "${fieldName}" on record "${model},${id}" (field is undefined)`
                );
            }
            if (["one2many", "many2many"].includes(field.type)) {
                let ids = record[fieldName] ? record[fieldName].slice() : [];
                // fallback to command 6 when given a simple list of ids
                if (Array.isArray(value)) {
                    if (
                        value.reduce((hasOnlyInt, val) => hasOnlyInt && Number.isInteger(val), true)
                    ) {
                        value = [[6, 0, value]];
                    }
                }
                // interpret commands
                for (const command of value || []) {
                    if (command[0] === 0) {
                        // CREATE
                        const newId = this.mockCreate(field.relation, command[2]);
                        ids.push(newId);
                    } else if (command[0] === 1) {
                        // UPDATE
                        this.mockWrite(field.relation, [[command[1]], command[2]]);
                    } else if (command[0] === 2 || command[0] === 3) {
                        // DELETE or FORGET
                        ids.splice(ids.indexOf(command[1]), 1);
                    } else if (command[0] === 4) {
                        // LINK_TO
                        if (!ids.includes(command[1])) {
                            ids.push(command[1]);
                        }
                    } else if (command[0] === 5) {
                        // DELETE ALL
                        ids = [];
                    } else if (command[0] === 6) {
                        // REPLACE WITH
                        // copy array to avoid leak by reference (eg. of default data)
                        ids = [...command[2]];
                    } else {
                        throw Error(
                            `Command "${JSON.stringify(
                                value
                            )}" not supported by the MockServer on field "${fieldName}" on record "${model},${id}"`
                        );
                    }
                }
                record[fieldName] = ids;
            } else if (field.type === "many2one") {
                if (value) {
                    const relRecord = this.models[field.relation].records.find(
                        (r) => r.id === value
                    );
                    if (!relRecord && ensureIntegrity) {
                        throw Error(
                            `Wrong id "${JSON.stringify(
                                value
                            )}" for a many2one on field "${fieldName}" on record "${model},${id}"`
                        );
                    }
                    record[fieldName] = value;
                } else {
                    record[fieldName] = false;
                }
            } else {
                record[fieldName] = value;
            }
        }
    }

    getUnusedID(modelName) {
        const model = this.models[modelName];
        return (
            model.records.reduce((max, record) => {
                if (!Number.isInteger(record.id)) {
                    return max;
                }
                return Math.max(record.id, max);
            }, 0) + 1
        );
    }

    applyDefaults(model, record) {
        record.display_name = record.display_name || record.name;
        for (const fieldName in model.fields) {
            if (fieldName === "id") {
                continue;
            }
            if (!(fieldName in record)) {
                if ("default" in model.fields[fieldName]) {
                    const def = model.fields[fieldName].default;
                    record[fieldName] = typeof def === "function" ? def.call(this) : def;
                } else if (["one2many", "many2many"].includes(model.fields[fieldName].type)) {
                    record[fieldName] = [];
                } else {
                    record[fieldName] = false;
                }
            }
        }
    }
}

// -----------------------------------------------------------------------------
// MockServer deployment helper
// -----------------------------------------------------------------------------

export function makeMockServer(serverData, mockRPC) {
    serverData = serverData || {};
    const mockServer = new MockServer(serverData, {
        debug: QUnit.config.debug,
    });
    const _mockRPC = async (route, args = {}) => {
        let res;
        if (mockRPC) {
            res = await mockRPC(route, args);
        }
        if (res === undefined) {
            res = await mockServer.performRPC(route, args);
        }
        return res;
    };
    const rpcService = makeFakeRPCService(_mockRPC);
    patchWithCleanup(browser, {
        fetch: makeMockFetch(_mockRPC),
    });
    // Replace RPC service
    serviceRegistry.add("rpc", rpcService, { force: true });
}
