/** @odoo-module **/

import { registry } from "./registry";

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
    FORGET: 3,
    forget(id) {
        return [x2ManyCommands.FORGET, id, false];
    },
    // (4, id[, _])
    LINK_TO: 4,
    linkTo(id) {
        return [x2ManyCommands.LINK_TO, id, false];
    },
    // (5[, _[, _]])
    DELETE_ALL: 5,
    deleteAll() {
        return [x2ManyCommands.DELETE_ALL, false, false];
    },
    // (6, _, ids) replaces all linked records with provided ids
    REPLACE_WITH: 6,
    replaceWith(ids) {
        return [x2ManyCommands.REPLACE_WITH, false, ids];
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

export class ORM {
    constructor(rpc, user) {
        this.rpc = rpc;
        this.user = user;
        this._silent = false;
    }

    get silent() {
        return Object.assign(Object.create(this), { _silent: true });
    }

    call(model, method, args = [], kwargs = {}) {
        validateModel(model);
        const url = `/web/dataset/call_kw/${model}/${method}`;
        const fullContext = Object.assign({}, this.user.context, kwargs.context || {});
        const fullKwargs = Object.assign({}, kwargs, { context: fullContext });
        const params = {
            model,
            method,
            args,
            kwargs: fullKwargs,
        };
        return this.rpc(url, params, { silent: this._silent });
    }

    create(model, records, kwargs = {}) {
        validateArray("records", records);
        for (const record of records) {
            validateObject("record", record);
        }
        return this.call(model, "create", records, kwargs);
    }

    nameGet(model, ids, kwargs = {}) {
        validatePrimitiveList("ids", "number", ids);
        if (!ids.length) {
            return Promise.resolve([]);
        }
        return this.call(model, "name_get", [ids], kwargs);
    }

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

    readGroup(model, domain, fields, groupby, kwargs = {}) {
        validateArray("domain", domain);
        validatePrimitiveList("fields", "string", fields);
        validatePrimitiveList("groupby", "string", groupby);
        return this.call(model, "read_group", [], { ...kwargs, domain, fields, groupby });
    }

    search(model, domain, kwargs = {}) {
        validateArray("domain", domain);
        return this.call(model, "search", [domain], kwargs);
    }

    searchRead(model, domain, fields, kwargs = {}) {
        validateArray("domain", domain);
        if (fields) {
            validatePrimitiveList("fields", "string", fields);
        }
        return this.call(model, "search_read", [], { ...kwargs, domain, fields });
    }

    searchCount(model, domain, kwargs = {}) {
        validateArray("domain", domain);
        return this.call(model, "search_count", [domain], kwargs);
    }

    unlink(model, ids, kwargs = {}) {
        validatePrimitiveList("ids", "number", ids);
        if (!ids.length) {
            return true;
        }
        return this.call(model, "unlink", [ids], kwargs);
    }

    webReadGroup(model, domain, fields, groupby, kwargs = {}) {
        validateArray("domain", domain);
        validatePrimitiveList("fields", "string", fields);
        validatePrimitiveList("groupby", "string", groupby);
        return this.call(model, "web_read_group", [], {
            ...kwargs,
            groupby,
            domain,
            fields,
        });
    }

    webSearchRead(model, domain, fields, kwargs = {}) {
        validateArray("domain", domain);
        validatePrimitiveList("fields", "string", fields);
        return this.call(model, "web_search_read", [], { ...kwargs, domain, fields });
    }

    write(model, ids, data, kwargs = {}) {
        validatePrimitiveList("ids", "number", ids);
        validateObject("data", data);
        return this.call(model, "write", [ids, data], kwargs);
    }
}

/**
 * Note:
 *
 * when we will need a way to configure a rpc (for example, to setup a "shadow"
 * flag, or some way of not displaying errors), we can use the following api:
 *
 * this.orm = useService('orm');
 *
 * ...
 *
 * const result = await this.orm.withOption({shadow: true}).read('res.partner', [id]);
 */
export const ormService = {
    dependencies: ["rpc", "user"],
    async: [
        "call",
        "create",
        "nameGet",
        "read",
        "readGroup",
        "search",
        "searchRead",
        "unlink",
        "webSearchRead",
        "write",
    ],
    start(env, { rpc, user }) {
        return new ORM(rpc, user);
    },
};

registry.category("services").add("orm", ormService);
