import { MockServer, models } from "@web/../tests/web_test_helpers";

const ids_by_model = {
    DiscussApp: [],
    "mail.thread": ["model", "id"],
    Rtc: [],
    Store: [],
};

/** Sentinel for "no explicit value given". */
const NO_VALUE = Symbol("NO_VALUE");

export class StoreAttr {
    constructor(store, field_name, value, { predicate = null, sudo = false } = {}) {
        this.store = store;
        this.field_name = field_name;
        this.value = value === undefined ? NO_VALUE : value;
        this.predicate = predicate;
        this.sudo = sudo;
    }

    _get_value(record, model = null) {
        if (this.value === NO_VALUE && record != null && model && model._fields[this.field_name]) {
            return record[this.field_name];
        }
        if (typeof this.value === "function") {
            return record == null ? this.value() : this.value(record);
        }
        if (this.value === NO_VALUE) {
            return null;
        }
        return this.value;
    }

    _identity() {
        return [this.constructor.name, this.field_name, this.predicate, this.sudo, this.value];
    }
}

export class StoreRelation extends StoreAttr {
    constructor(
        store,
        records_or_field_name,
        fields,
        {
            as_thread = false,
            dynamic_fields = null,
            fields_params = null,
            only_data = false,
            predicate = null,
            sudo = false,
            value,
        } = {}
    ) {
        const field_name = typeof records_or_field_name === "string" ? records_or_field_name : null;
        super(store, field_name, value, { predicate, sudo });
        this.records = records_or_field_name instanceof models.Model ? records_or_field_name : null;
        this.as_thread = as_thread;
        this.dynamic_fields = dynamic_fields;
        this.fields = fields;
        this.fields_params = fields_params;
        this.only_data = only_data;
        // format fields early to ensure the final shape is used whenever possible
        if (this.records) {
            this.fields = this.store._format_fields(this.fields, this.records, this.fields_params);
            this.fields_params = null;
        }
    }

    _get_value(record, model) {
        let records = super._get_value(record, model);
        if (this.value === NO_VALUE) {
            if (!records) {
                const res_model_field = model._fields["res_model"] ? "res_model" : "model";
                if (this.field_name === "thread" && !model._fields["thread"]) {
                    const res_model = record[res_model_field];
                    const res_id = record["res_id"];
                    if (res_model && res_id) {
                        records = model.env[res_model].browse(res_id);
                    }
                }
            } else {
                records = model.env[model._fields[this.field_name].relation].browse(records);
            }
        }
        return this._copy_with_records(records, record, model);
    }

    _copy_with_records(records, calling_record, model) {
        const is_fake_field = this.value !== NO_VALUE && !(records instanceof models.Model);
        let field_list;
        if (!is_fake_field && records && records.length) {
            field_list = this.store._format_fields(this.fields, records, this.fields_params);
            if (this.dynamic_fields) {
                const callingRecordset =
                    calling_record != null && model
                        ? model.env[model._name].browse(calling_record.id)
                        : null;
                if (typeof this.dynamic_fields === "string") {
                    const method = Store._get_fields_method(callingRecordset, this.dynamic_fields);
                    if (!method) {
                        throw new Error(`unexpected dynamic_fields: '${this.dynamic_fields}'`);
                    }
                    method.call(callingRecordset, field_list);
                } else if (typeof this.dynamic_fields === "function") {
                    this.dynamic_fields(field_list, calling_record);
                } else {
                    throw new Error(`unexpected dynamic_fields: '${this.dynamic_fields}'`);
                }
            }
        } else {
            field_list = [];
        }
        return new this.constructor(this.store, is_fake_field ? null : records, field_list, {
            as_thread: this.as_thread,
            fields_params: this.fields_params,
            only_data: this.only_data,
            value: is_fake_field ? records : undefined,
        });
    }

    _add_to_store(store, target, key) {
        store.add(this.records, this.fields, { as_thread: this.as_thread, ignore_empty: true });
    }

    _identity() {
        return [
            ...super._identity(),
            this.records ? this.records._name : null,
            this.records ? this.records.map((r) => r.id) : null,
            this.as_thread,
            this.dynamic_fields,
            this.fields,
            this.fields_params,
            this.only_data,
        ];
    }
}

export class StoreOne extends StoreRelation {
    constructor() {
        super(...arguments);
        if (this.records && this.records.length > 1) {
            throw new Error(`One received ${this.records}`);
        }
    }

    _add_to_store(store, target, key) {
        super._add_to_store(store, target, key);
        if (!this.only_data) {
            target[key] = Store._get_one_id(this.records, this.as_thread);
        }
    }
}

export class StoreMany extends StoreRelation {
    constructor(store, records_or_field_name, fields, options = {}) {
        super(store, records_or_field_name, fields, options);
        this.mode = options.mode || "REPLACE";
        this.sort = options.sort ?? null;
    }

    _copy_with_records(records, calling_record, model) {
        if (records == null) {
            records = [];
        }
        const res = super._copy_with_records(records, calling_record, model);
        res.mode = this.mode;
        res.sort = this.sort;
        return res;
    }

    _sort_records() {
        if (this.sort && this.records) {
            const cmp =
                typeof this.sort === "function"
                    ? this.sort
                    : (a, b) =>
                          a[this.sort] < b[this.sort] ? -1 : a[this.sort] > b[this.sort] ? 1 : 0;
            this.records.sort(cmp);
            this.sort = null;
        }
    }

    _add_to_store(store, target, key) {
        this._sort_records();
        super._add_to_store(store, target, key);
        const has_something_to_write =
            this.value !== NO_VALUE ||
            (this.records && this.records.length) ||
            this.mode === "REPLACE";
        if (!this.only_data && has_something_to_write) {
            const rel_val = this._get_id();
            if (this.mode === "REPLACE" || !(key in target)) {
                target[key] = rel_val;
                return;
            }
            if (target[key].length && !Array.isArray(target[key][0])) {
                target[key] = [["REPLACE", target[key]]];
            }
            target[key] = target[key].concat(rel_val);
        }
    }

    _get_id() {
        if (this.value !== NO_VALUE) {
            return this._prepend_mode(this.value);
        }
        this._sort_records();
        let res = [];
        if (this.records && this.records.length) {
            const Model = this.records.env[this.records._name];
            res = this.records.map((record) =>
                Store._get_one_id(Model.browse(record.id), this.as_thread)
            );
        }
        return this._prepend_mode(res);
    }

    _prepend_mode(res) {
        if (this.mode === "ADD") {
            return [["ADD", res]];
        }
        if (this.mode === "DELETE") {
            return [["DELETE", res]];
        }
        return res;
    }
}

function isPlainDict(value) {
    return (
        typeof value === "object" &&
        value !== null &&
        !Array.isArray(value) &&
        !(value instanceof StoreAttr) &&
        !(value instanceof StoreFieldList) &&
        !(value instanceof models.Model)
    );
}

function sortObjectKeys(obj) {
    const res = {};
    for (const key of Object.keys(obj).sort()) {
        res[key] = obj[key];
    }
    return res;
}

export class StoreFieldList {
    constructor(store, records) {
        // records for which the field list will apply. Useful to pre-compute values in batch.
        this.store = store;
        this.records = records ?? null;
        this._fields = [];
        this._internal_field_list = store._internal_store
            ? new StoreFieldList(store._internal_store, records)
            : null;
    }

    get length() {
        return this._fields.length;
    }

    [Symbol.iterator]() {
        return this._fields[Symbol.iterator]();
    }

    /** Store.Target of the field list. Useful to adapt fields depending on the receivers. */
    get target() {
        return this.store.target;
    }

    append(field, { internal = false } = {}) {
        if (!internal || this.is_for_internal_users()) {
            this._fields.push(field);
        } else if (this._internal_field_list) {
            this._internal_field_list.append(field);
        }
    }

    extend(fields, { internal = false } = {}) {
        const items = fields instanceof StoreFieldList ? [...fields] : fields;
        if (!internal || this.is_for_internal_users()) {
            this._fields.push(...items);
        } else if (this._internal_field_list) {
            this._internal_field_list.extend(items);
        }
    }

    attr(field_name, value, { predicate = null, sudo = false, internal = false } = {}) {
        if (this.records != null && value === undefined && !predicate && !sudo) {
            this.append(field_name, { internal });
        } else {
            this.append(new StoreAttr(this.store, field_name, value, { predicate, sudo }), {
                internal,
            });
        }
    }

    from_method(method_name, { internal = false, ...fields_params } = {}) {
        const method = Store._get_fields_method(this.records, method_name);
        if (!method) {
            throw new Error(
                `unexpected method name format: '${method_name}' for records: '${this.records}'`
            );
        }
        if (!internal || this.is_for_internal_users()) {
            method.call(this.records, this, fields_params);
        } else if (this._internal_field_list) {
            method.call(this.records, this._internal_field_list, fields_params);
        }
    }

    one(record_or_field_name, fields, { internal = false, ...rel } = {}) {
        this.append(new StoreOne(this.store, record_or_field_name, fields, rel), { internal });
    }

    many(records_or_field_name, fields, { internal = false, ...rel } = {}) {
        this.append(new StoreMany(this.store, records_or_field_name, fields, rel), { internal });
    }

    is_for_current_user() {
        // In the mock, stores never carry a bus target, so this is always the current user.
        return this.target.channel == null && this.target.subchannel == null;
    }

    is_for_internal_users() {
        // In the mock, stores never carry a bus target, so the check is based on the env user.
        if (this.target.channel != null || this.target.subchannel != null) {
            return false;
        }
        const env = this.records ? this.records.env : MockServer.env;
        const ResUsers = env["res.users"];
        if (ResUsers._is_public(env.uid)) {
            return false;
        }
        const [user] = ResUsers.read(env.uid);
        return !user.share;
    }

    _identity() {
        return [
            "FieldList",
            this.records ? this.records._name : null,
            this.records ? this.records.map((r) => r.id) : null,
            [...this._fields],
        ];
    }
}

class Store {
    constructor(bus_channel, bus_subchannel, kwargs) {
        this.add_depth = 0;
        this.already_done = new Set();
        // data[model_name] is a Map indexed by the record index ("" for singletons)
        this.data = new Map();
        this.data_id = null;
        this.is_executing_operation_queue = false;
        this.operation_queue = [];
        this.target = new Store.Target(bus_channel, bus_subchannel);
        this._internal_store = null;
        this._auto_send = true;
    }

    /**
     * Add records to the store.
     *
     * Fields can be defined in multiple ways:
     * - as a string: the name of a `_store_<name>_fields` method on the records that is called
     *   with a Store.FieldList as first argument, and optional fields_params as other arguments.
     * - as a callable: a function that is called with a Store.FieldList as first argument.
     * - as a list: list of field names. Data for fields come from _read_format().
     * - as a dict: mapping of field names to static values.
     */
    add(records, fields, options = {}) {
        if (!this.is_executing_operation_queue) {
            this.operation_queue.push(() => this._add(records, fields, options));
            return this;
        }
        return this._add(records, fields, options);
    }

    _add(records, fields, { as_thread = false, fields_params = null, ignore_empty = false } = {}) {
        if (!records) {
            return this;
        }
        if (!(records instanceof models.Model)) {
            throw new Error(`Store.add() expects a recordset, got: ${records}`);
        }
        if (!records.length) {
            return this;
        }
        // call _format_fields before checking identifier to always compare the final shape
        const field_list = this._format_fields(fields, records, fields_params);
        const identifier = Store._deep_freeze([
            records._name,
            records.map((r) => r.id),
            field_list,
            as_thread,
        ]);
        if (this.already_done.has(identifier)) {
            return this;
        }
        this.already_done.add(identifier);
        this.add_depth += 1;
        try {
            this._add_field_list(field_list, { as_thread, ignore_empty });
            return this;
        } finally {
            this.add_depth -= 1;
            if (this.add_depth === 0) {
                this.already_done.clear();
            }
        }
    }

    /**
     * Add global values to the store. Global values are stored in the Store singleton
     * (mail.store service) on the client side.
     */
    add_global_values(values) {
        if (!this.is_executing_operation_queue) {
            this.operation_queue.push(() => this._add_global_values(values));
            return this;
        }
        return this._add_global_values(values);
    }

    _add_global_values(values) {
        this.add_model_values("Store", values);
        return this;
    }

    /** Add values to a model in the store, for JS records without a corresponding python record. */
    add_model_values(model_name, values, options = {}) {
        if (!this.is_executing_operation_queue) {
            this.operation_queue.push(() => this._add_model_values(model_name, values, options));
            return this;
        }
        return this._add_model_values(model_name, values, options);
    }

    _add_model_values(model_name, values, { id_data = null, ignore_empty = false } = {}) {
        if (!values) {
            return this;
        }
        const data_list = [];
        this._add_abstract_fields_value(this._format_fields(values), data_list);
        const index = this._get_record_index(model_name, [id_data || {}, ...data_list]);
        for (const data of data_list) {
            this._add_values(data, model_name, index);
        }
        const target = this._data_at(model_name, index);
        if (id_data && (Object.keys(target).length || !ignore_empty)) {
            this._add_values(id_data, model_name, index);
        }
        if ("_DELETE" in target) {
            delete target._DELETE;
        }
        return this;
    }

    _add_field_list(field_list, { as_thread = false, ignore_empty = false } = {}) {
        if (field_list.length && field_list.records && field_list.records.length) {
            const records = field_list.records;
            const model_name = records._name;
            const records_data_list = this._get_records_data_list(field_list, ignore_empty);
            records.forEach((record, i) => {
                for (const record_data of records_data_list[i]) {
                    let name = model_name;
                    const id_data = { id: record.id };
                    if (as_thread) {
                        name = "mail.thread";
                        id_data.model = model_name;
                    }
                    this.add_model_values(name, record_data, { id_data, ignore_empty });
                }
            });
        }
        if (this._internal_store) {
            this._internal_store._add_field_list(field_list._internal_field_list, {
                as_thread,
                ignore_empty,
            });
        }
        return this;
    }

    /** Delete records from the store. */
    delete(records, options = {}) {
        if (!this.is_executing_operation_queue) {
            this.operation_queue.push(() => this._delete(records, options));
            return this;
        }
        return this._delete(records, options);
    }

    _delete(records, { as_thread = false } = {}) {
        if (!records || !records.length) {
            return this;
        }
        const model_name = as_thread ? "mail.thread" : records._name;
        for (const record of records) {
            const values = as_thread ? { id: record.id, model: records._name } : { id: record.id };
            const index = this._get_record_index(model_name, [values]);
            this._add_values(values, model_name, index);
            this._data_at(model_name, index)._DELETE = true;
        }
        return this;
    }

    /** Add values to the store for the current data request. */
    resolve_data_request(values) {
        const data_id = this.data_id;
        if (!this.is_executing_operation_queue) {
            this.operation_queue.push(() => this._resolve_data_request(values, data_id));
            return this;
        }
        return this._resolve_data_request(values, data_id);
    }

    _resolve_data_request(values, data_id) {
        if (!data_id) {
            return this;
        }
        const data_list = [];
        this._add_abstract_fields_value(this._format_fields(values ?? [{}]), data_list);
        for (const data of data_list) {
            this.add_model_values("DataResponse", { id: data_id, _resolve: true, ...data });
        }
        return this;
    }

    /**
     * Do not call directly. Executes pending operations and returns the aggregated result.
     * Automatically invoked by `as_dict()`.
     */
    _build_result(disable_auto_send = true) {
        if (disable_auto_send) {
            this._auto_send = false;
            if (this._internal_store) {
                this._internal_store._auto_send = false;
            }
        }
        this.is_executing_operation_queue = true;
        try {
            for (const fn of this.operation_queue) {
                fn();
            }
            this.operation_queue = [];
        } finally {
            this.is_executing_operation_queue = false;
        }
        const res = {};
        for (const model_name of [...this.data.keys()].sort()) {
            const records = this.data.get(model_name);
            if ((ids_by_model[model_name] ?? ["id"]).length === 0) {
                // singletons have a single item (the "" index), the wrapping list can be omitted
                res[model_name] = sortObjectKeys(records.get("") ?? {});
            } else {
                const vals = [...records.values()]
                    .filter((record) => Object.keys(record).length)
                    .map((record) => sortObjectKeys(record));
                if (vals.length) {
                    res[model_name] = vals;
                }
            }
        }
        return res;
    }

    /** Returns a dictionary representing the aggregated result of all store commands. */
    as_dict() {
        return this._build_result(false);
    }

    _get_records_data_list(field_list, ignore_empty) {
        const records = field_list.records;
        const fields = [...field_list];
        const abstractFields = fields.filter((f) => f instanceof StoreAttr || isPlainDict(f));
        const standardFields = fields.filter((f) => !abstractFields.includes(f));
        const records_data_list = records.map(() => []);
        if (standardFields.length || !ignore_empty) {
            const read = records._read_format(
                records.map((r) => r.id),
                standardFields,
                false
            );
            read.forEach((data, i) => records_data_list[i].push(data));
        }
        records.forEach((record, i) => {
            this._add_abstract_fields_value(abstractFields, records_data_list[i], record, records);
        });
        return records_data_list;
    }

    _add_abstract_fields_value(abstractFields, data_list, record = null, model = null) {
        for (const field of abstractFields) {
            if (isPlainDict(field)) {
                data_list.push(field);
            } else if (!field.predicate || field.predicate(record)) {
                data_list.push({ [field.field_name]: field._get_value(record, model) });
            }
        }
    }

    _get_record_index(model_name, data_list) {
        const values = {};
        for (const data of data_list) {
            if (isPlainDict(data)) {
                Object.assign(values, data);
            }
        }
        const ids = ids_by_model[model_name] ?? ["id"];
        for (const i of ids) {
            if (!values[i]) {
                throw new Error(`missing id ${i} in ${model_name}: ${JSON.stringify(values)}`);
            }
        }
        return ids.map((i) => values[i]).join("\x00");
    }

    _data_at(model_name, index) {
        if (!this.data.has(model_name)) {
            this.data.set(model_name, new Map());
        }
        const records = this.data.get(model_name);
        if (!records.has(index)) {
            records.set(index, {});
        }
        return records.get(index);
    }

    _format_fields(fields, records = null, fields_params = null) {
        const field_list = new StoreFieldList(this, records);
        if (typeof fields === "string") {
            const method = Store._get_fields_method(records, fields);
            if (!method) {
                throw new Error(`unexpected fields format: '${fields}' for records: '${records}'`);
            }
            method.call(records, field_list, fields_params ?? {});
        } else if (typeof fields === "function") {
            fields(field_list);
        } else if (fields instanceof StoreFieldList) {
            field_list.extend(fields);
            if (fields._internal_field_list) {
                field_list.extend(fields._internal_field_list, { internal: true });
            }
        } else if (Array.isArray(fields)) {
            field_list.extend(fields);
        } else if (isPlainDict(fields)) {
            for (const [key, value] of Object.entries(fields)) {
                field_list.append(new StoreAttr(this, key, value));
            }
        } else if (fields != null) {
            throw new Error(`unexpected fields format: '${fields}' for records: '${records}'`);
        }
        return field_list;
    }

    _add_values(values, model_name, index) {
        const target = this._data_at(model_name, index);
        for (const [key, val] of Object.entries(values)) {
            if (key === "_DELETE") {
                throw new Error(`invalid key ${key} in ${model_name}: ${JSON.stringify(values)}`);
            }
            if (val instanceof StoreRelation) {
                val._add_to_store(this, target, key);
            } else {
                target[key] = val;
            }
        }
    }

    toJSON() {
        throw Error(
            "Converting Store to JSON is not supported, you might want to call 'as_dict()' instead."
        );
    }

    static _get_fields_method(records, method_name) {
        if (
            !(records instanceof models.Model) ||
            !method_name.startsWith("_store_") ||
            !method_name.endsWith("_fields")
        ) {
            return null;
        }
        if (typeof records[method_name] === "function") {
            return records[method_name];
        }
        // mail.thread is a mixin in real Odoo: its store methods (e.g. `_store_thread_fields`)
        // are available on every thread record. The mock models don't share that base, so we
        // fall back to the mail.thread mock model, bound to the calling record.
        const MailThread = records.env["mail.thread"];
        if (MailThread && typeof MailThread[method_name] === "function") {
            return MailThread[method_name];
        }
        return null;
    }

    static _get_one_id(records, as_thread) {
        if (!records || !records.length) {
            return false;
        }
        if (as_thread) {
            return { id: records[0].id, model: records._name };
        }
        return records[0].id;
    }

    /** Recursively convert a data structure into a stable string identifier that can be compared. */
    static _deep_freeze(obj) {
        if (obj instanceof StoreFieldList || obj instanceof StoreAttr) {
            return Store._deep_freeze(obj._identity());
        }
        if (Array.isArray(obj)) {
            return `[${obj.map((item) => Store._deep_freeze(item)).join(",")}]`;
        }
        if (obj instanceof models.Model) {
            return `model:${obj._name}:[${obj.map((r) => r.id).join(",")}]`;
        }
        if (obj && typeof obj === "object") {
            return `{${Object.keys(obj)
                .sort()
                .map((k) => `${k}:${Store._deep_freeze(obj[k])}`)
                .join(",")}}`;
        }
        if (typeof obj === "function") {
            return `fn:${obj.toString()}`;
        }
        return String(obj);
    }
}

Store.Target = class {
    constructor(channel, subchannel) {
        this.channel = channel ?? null;
        this.subchannel = subchannel ?? null;
    }
};
Store.Attr = StoreAttr;
Store.Relation = StoreRelation;
Store.One = StoreOne;
Store.Many = StoreMany;
Store.FieldList = StoreFieldList;

export { Store };
