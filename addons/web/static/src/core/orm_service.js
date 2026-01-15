import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { user } from "@web/core/user";
import { Domain } from "@web/core/domain";

/**
 * This ORM service is the standard way to interact with the ORM in python from
 * the javascript codebase.
 */

// -----------------------------------------------------------------------------
// ORM
// -----------------------------------------------------------------------------

/**
 * One2many and Many2many fields expect a special command to manipulate the
 * relation they implement.
 *
 * Internally, each command is a 3-elements tuple where the first element is a
 * mandatory integer that identifies the command, the second element is either
 * the related record id to apply the command on (commands update, delete,
 * unlink and link) either 0 (commands create, clear and set), the third
 * element is either the ``values`` to write on the record (commands create
 * and update) either the new ``ids`` list of related records (command set),
 * either 0 (commands delete, unlink, link, and clear).
 */
export const x2ManyCommands = {
    // (0, virtualID | false, { values })
    CREATE: 0,
    create(virtualID, values) {
        delete values.id;
        return [x2ManyCommands.CREATE, virtualID || false, values];
    },
    // (1, id, { values })
    UPDATE: 1,
    update(id, values) {
        delete values.id;
        return [x2ManyCommands.UPDATE, id, values];
    },
    // (2, id[, _])
    DELETE: 2,
    delete(id) {
        return [x2ManyCommands.DELETE, id, false];
    },
    // (3, id[, _]) removes relation, but not linked record itself
    UNLINK: 3,
    unlink(id) {
        return [x2ManyCommands.UNLINK, id, false];
    },
    // (4, id[, _])
    LINK: 4,
    link(id) {
        return [x2ManyCommands.LINK, id, false];
    },
    // (5[, _[, _]])
    CLEAR: 5,
    clear() {
        return [x2ManyCommands.CLEAR, false, false];
    },
    // (6, _, ids) replaces all linked records with provided ids
    SET: 6,
    set(ids) {
        return [x2ManyCommands.SET, false, ids];
    },
};

function validateModel(value) {
    if (typeof value !== "string" || value.length === 0) {
        throw new Error(`Invalid model name: ${value}`);
    }
}
function validatePrimitiveList(name, type, value) {
    if (!Array.isArray(value) || value.some((val) => typeof val !== type)) {
        throw new Error(`Invalid ${name} list: ${value}`);
    }
}
function validateObject(name, obj) {
    if (typeof obj !== "object" || obj === null || Array.isArray(obj)) {
        throw new Error(`${name} should be an object`);
    }
}
function validateArray(name, array) {
    if (!Array.isArray(array)) {
        throw new Error(`${name} should be an array`);
    }
}

export const UPDATE_METHODS = [
    "unlink",
    "create",
    "write",
    "web_save",
    "web_save_multi",
    "action_archive",
    "action_unarchive",
];

export class ORM {
    constructor() {
        this.rpc = rpc; // to be overridable by the SampleORM
        /** @protected */
        this._silent = false;
        this._cache = false;
    }

    /** @returns {ORM} */
    get silent() {
        return Object.assign(Object.create(this), { _silent: true });
    }

    /**
     * @param {object} options
     * @returns {ORM}
     */
    cache(options = {}) {
        return Object.assign(Object.create(this), { _cache: options });
    }

    /**
     * @param {string} model
     * @param {string} method
     * @param {any[]} [args=[]]
     * @param {any} [kwargs={}]
     * @returns {Promise<any>}
     */
    call(model, method, args = [], kwargs = {}) {
        validateModel(model);
        const url = `/web/dataset/call_kw/${model}/${method}`;
        const fullContext = Object.assign({}, user.context, kwargs.context || {});
        const fullKwargs = Object.assign({}, kwargs, { context: fullContext });
        const params = {
            model,
            method,
            args,
            kwargs: fullKwargs,
        };
        return this.rpc(url, params, {
            silent: this._silent,
            cache: this._cache,
        });
    }

    /**
     * @param {string} model
     * @param {any[]} records
     * @param {any} [kwargs=[]]
     * @returns {Promise<number>}
     */
    create(model, records, kwargs = {}) {
        validateArray("records", records);
        for (const record of records) {
            validateObject("record", record);
        }
        return this.call(model, "create", [records], kwargs);
    }

    /**
     * @param {string} model
     * @param {number[]} ids
     * @param {string[]} fields
     * @param {any} [kwargs={}]
     * @returns {Promise<any[]>}
     */
    read(model, ids, fields, kwargs = {}) {
        validatePrimitiveList("ids", "number", ids);
        if (fields) {
            validatePrimitiveList("fields", "string", fields);
        }
        if (!ids.length) {
            return Promise.resolve([]);
        }
        return this.call(model, "read", [ids, fields], kwargs);
    }

    /**
     * @param {string} model
     * @param {import("@web/core/domain").DomainListRepr} domain
     * @param {string[]} fields
     * @param {string[]} groupby
     * @param {any} [kwargs={}]
     * @returns {Promise<any[]>}
     */
    formattedReadGroup(model, domain, groupby, aggregates, kwargs = {}) {
        validateArray("domain", domain);
        validatePrimitiveList("groupby", "string", groupby);
        validatePrimitiveList("aggregates", "string", aggregates);
        return this.call(model, "formatted_read_group", [], {
            domain,
            groupby,
            aggregates,
            ...kwargs,
        }).then((res) => {
            for (const group of res) {
                group["__domain"] = Domain.and([domain, group["__extra_domain"]]).toList();
            }
            return res;
        });
    }

    /**
     * @param {string} model
     * @param {import("@web/core/domain").DomainListRepr} domain
     * @param {string[]} fields
     * @param {string[][]} grouping_sets
     * @param {any} [kwargs={}]
     * @returns {Promise<any[]>}
     */
    formattedReadGroupingSets(model, domain, grouping_sets, aggregates, kwargs = {}) {
        validateArray("domain", domain);
        validateArray("groupby", grouping_sets);
        validatePrimitiveList("aggregates", "string", aggregates);
        return this.call(model, "formatted_read_grouping_sets", [], {
            domain,
            grouping_sets,
            aggregates,
            ...kwargs,
        }).then((res) => {
            for (const groups of res) {
                for (const group of groups) {
                    group["__domain"] = Domain.and([domain, group["__extra_domain"]]).toList();
                }
            }
            return res;
        });
    }

    /**
     * @param {string} model
     * @param {import("@web/core/domain").DomainListRepr} domain
     * @param {any} [kwargs={}]
     * @returns {Promise<any[]>}
     */
    search(model, domain, kwargs = {}) {
        validateArray("domain", domain);
        return this.call(model, "search", [domain], kwargs);
    }

    /**
     * @param {string} model
     * @param {import("@web/core/domain").DomainListRepr} domain
     * @param {string[]} fields
     * @param {any} [kwargs={}]
     * @returns {Promise<any[]>}
     */
    searchRead(model, domain, fields, kwargs = {}) {
        validateArray("domain", domain);
        if (fields) {
            validatePrimitiveList("fields", "string", fields);
        }
        return this.call(model, "search_read", [], { ...kwargs, domain, fields });
    }

    /**
     * @param {string} model
     * @param {import("@web/core/domain").DomainListRepr} domain
     * @param {any} [kwargs={}]
     * @returns {Promise<number>}
     */
    searchCount(model, domain, kwargs = {}) {
        validateArray("domain", domain);
        return this.call(model, "search_count", [domain], kwargs);
    }

    /**
     * @param {string} model
     * @param {number[]} ids
     * @param {any} [kwargs={}]
     * @returns {Promise<boolean>}
     */
    unlink(model, ids, kwargs = {}) {
        validatePrimitiveList("ids", "number", ids);
        if (!ids.length) {
            return Promise.resolve(true);
        }
        return this.call(model, "unlink", [ids], kwargs);
    }

    /**
     * @param {string} model
     * @param {import("@web/core/domain").DomainListRepr} domain
     * @param {string[]} groupby
     * @param {string[]} aggregates
     * @param {any} [kwargs={}]
     * @returns {Promise<any[]>}
     */
    webReadGroup(model, domain, groupby, aggregates, kwargs = {}) {
        validateArray("domain", domain);
        validatePrimitiveList("aggregates", "string", aggregates);
        return this.call(model, "web_read_group", [], {
            domain,
            groupby,
            aggregates,
            ...kwargs,
        });
    }

    /**
     * @param {string} model
     * @param {number[]} ids
     * @param {any} [kwargs={}]
     * @param {Object} [kwargs.specification]
     * @param {Object} [kwargs.context]
     * @returns {Promise<any[]>}
     */
    webRead(model, ids, kwargs = {}) {
        validatePrimitiveList("ids", "number", ids);
        return this.call(model, "web_read", [ids], kwargs);
    }

    /**
     * @param {string} model
     * @param {number[]} ids
     * @param {object} [kwargs={}]
     * @param {object} [kwargs.context]
     * @param {string} [kwargs.field_name]
     * @param {number} [kwargs.offset]
     * @param {object} [kwargs.specification]
     * @returns {Promise<any[]>}
     */
    webResequence(model, ids, kwargs = {}) {
        validatePrimitiveList("ids", "number", ids);
        return this.call(model, "web_resequence", [ids], {
            ...kwargs,
            specification: kwargs.specification || {},
        });
    }

    /**
     * @param {string} model
     * @param {import("@web/core/domain").DomainListRepr} domain
     * @param {any} [kwargs={}]
     * @returns {Promise<any[]>}
     */
    webSearchRead(model, domain, kwargs = {}) {
        validateArray("domain", domain);
        return this.call(model, "web_search_read", [], { ...kwargs, domain });
    }

    /**
     * @param {string} model
     * @param {number[]} ids
     * @param {any} data
     * @param {any} [kwargs={}]
     * @returns {Promise<boolean>}
     */
    write(model, ids, data, kwargs = {}) {
        validatePrimitiveList("ids", "number", ids);
        validateObject("data", data);
        return this.call(model, "write", [ids, data], kwargs);
    }

    /**
     * @param {string} model
     * @param {number[]} ids
     * @param {any} data
     * @param {any} [kwargs={}]
     * @param {Object} [kwargs.specification]
     * @param {Object} [kwargs.context]
     * @returns {Promise<any[]>}
     */
    webSave(model, ids, data, kwargs = {}) {
        validatePrimitiveList("ids", "number", ids);
        validateObject("data", data);
        return this.call(model, "web_save", [ids, data], kwargs);
    }

    /**
     * @param {string} model
     * @param {number[]} ids
     * @param {Object[]} data
     * @param {Object} [kwargs={}]
     * @param {Object} [kwargs.specification]
     * @param {Object} [kwargs.context]
     * @returns {Promise<any[]>}
     */
    async webSaveMulti(model, ids, data, kwargs = {}) {
        validatePrimitiveList("ids", "number", ids);
        validateArray("data", data);
        data.forEach((d) => {
            validateObject("data item", d);
        });
        return this.call(model, "web_save_multi", [ids, data], kwargs);
    }
}

/**
 * Note:
 *
 * To hide RPC errors, use the following API:
 *
 * this.orm = useService('orm');
 * ...
 * const result = await this.orm.silent.read('res.partner', [id]);
 */
export const ormService = {
    async: [
        "call",
        "create",
        "nameGet",
        "read",
        "formattedReadGroup",
        "webReadGroup",
        "search",
        "searchRead",
        "unlink",
        "webResequence",
        "webSearchRead",
        "write",
    ],
    start() {
        return new ORM();
    },
};

registry.category("services").add("orm", ormService);
