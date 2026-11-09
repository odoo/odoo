import { computed, signal } from "@odoo/owl";
import { user } from "@web/core/user";
import { Model } from "@web/model/model";
import { toCommands } from "@web/model/store/commands";
import { Model as StoreModel } from "@web/model/store/model";
import { RecordStore } from "@web/model/store/store";

/**
 * @typedef {{
 *  resModel: string;
 *  fields: Record<string, any>;
 *  fieldNames: string[];
 *  context: Record<string, any>;
 *  resId: number | false;
 *  resIds: number[];
 * }} NewRelationalModelParams
 */

const X2MANY_TYPES = ["one2many", "many2many"];
const RELATIONAL_TYPES = ["many2one", ...X2MANY_TYPES];

/**
 * View model built on top of the record store.
 *
 * It shows one record at a time (the "root"): it reads it with `web_read`,
 * creates new ones from `onchange` defaults, and saves them with `web_save`.
 *
 * The model holds almost no state of its own. Field values live in the store,
 * as signals: components read them directly (`record.name()`) and re-render
 * when they change, so there is no `notify()` and no update bus. The model
 * only owns two signals: `root`, the displayed record, and `resId`, its id
 * (false while it is new).
 *
 * Current limits: no onchange when a field changes, x2many fields are read
 * only, and x2many default values are ignored.
 */
export class NewRelationalModel extends Model {
    /**
     * @param {NewRelationalModelParams} params
     */
    setup(params) {
        this.resModel = params.resModel;
        this.fields = params.fields;
        this.context = params.context;
        /** ids reachable with the pager */
        this.resIds = [...params.resIds];

        this.store = new RecordStore(
            buildStoreParams(params.resModel, params.fields, params.fieldNames)
        );
        this.specification = buildSpecification(params.fields, params.fieldNames);

        /** the displayed record (a record of the store), null until loaded */
        this.root = signal(/** @type {StoreModel | null} */ (null));
        /** id of the displayed record, false while it is new */
        this.resId = signal(params.resId);
        /** store clock when the current new record was created, see `isDirty` */
        this.createdAt = 0;
        /** what view modifiers read, e.g. `invisible="state == 'done'"` */
        this.evalContext = computed(() => this.root() && this.makeEvalContext(this.root()));
    }

    /**
     * Loads a record and displays it. `resId: false` displays a new record.
     *
     * Also called by `useModel` with the search params, which have no `resId`:
     * the current record is reloaded.
     *
     * @param {{ resId?: number | false }} [params]
     */
    async load({ resId = this.resId() } = {}) {
        const record = resId ? await this.fetchRecord(resId) : await this.newRecord();
        this.root.set(record);
        this.resId.set(resId);
    }

    /**
     * Saves the root record if it has changes (or is new).
     */
    async save() {
        const record = this.root();
        if (!this.store.isDirty(record)) {
            return;
        }
        const isNew = this.store.isNew(record);
        // `version` tells `ack` which changes were sent: edits made while the
        // request is pending stay dirty
        const { vals, version } = toCommands(record);
        for (const name in vals) {
            if (this.fields[name].readonly) {
                delete vals[name];
            }
        }
        const [values] = await this.orm.webSave(this.resModel, isNew ? [] : [record.id], vals, {
            specification: this.specification,
            context: this.readContext(),
        });
        if (isNew) {
            // same record object, new id: whatever points to it stays valid
            this.store.rekey(record, values.id);
            this.resIds.push(values.id);
        }
        this.store.ack(record, version);
        // server values computed by the save (e.g. computed fields)
        this.store.load(this.resModel, values);
        this.resId.set(values.id);
    }

    /**
     * Drops the local changes of the root record. A new record is dropped
     * entirely: the caller decides what to display instead.
     */
    discard() {
        this.store.discard(this.root());
    }

    /**
     * True when the user changed something that is not saved yet. Reactive.
     */
    isDirty() {
        const record = this.root();
        if (!record || !this.store.isDirty(record)) {
            return false;
        }
        // The store considers a new record dirty from the start, as its default
        // values are local writes. For the view, it is dirty once the user
        // edited it, i.e. once something was written after its creation.
        return !this.store.isNew(record) || this.store.clock > this.createdAt;
    }

    /**
     * True when the root record is not saved yet. Reactive.
     */
    isNew() {
        return !this.resId();
    }

    // -------------------------------------------------------------------------
    // Private
    // -------------------------------------------------------------------------

    /**
     * Field values are getters, so that evaluating a modifier only reads (and
     * subscribes to) the fields it uses: `state == 'done'` re-evaluates when
     * `state` changes, not on every edit.
     *
     * @param {StoreModel} record
     */
    makeEvalContext(record) {
        const evalContext = {
            context: this.context,
            uid: user.userId,
            current_company_id: user.activeCompany?.id,
        };
        Object.defineProperty(evalContext, "id", {
            enumerable: true,
            get: () => (this.isNew() ? false : record.id),
        });
        for (const field of this.store.model(this.resModel).fields) {
            Object.defineProperty(evalContext, field.name, {
                enumerable: true,
                get: () => toPyValue(field.type, record[field.name]()),
            });
        }
        return evalContext;
    }

    /**
     * Context of the calls that return field values: binary fields come as
     * their size, not as their (possibly large) content.
     */
    readContext() {
        return { bin_size: true, ...this.context };
    }

    /**
     * @param {number} resId
     */
    async fetchRecord(resId) {
        const [values] = await this.orm.webRead(this.resModel, [resId], {
            specification: this.specification,
            context: this.readContext(),
        });
        return this.store.load(this.resModel, values);
    }

    async newRecord() {
        const { value } = await this.orm.call(
            this.resModel,
            "onchange",
            [[], {}, [], this.specification],
            { context: this.context }
        );
        const values = {};
        for (const [name, fieldValue] of Object.entries(value)) {
            const field = this.fields[name];
            if (field.type === "many2one") {
                // { id, display_name }: load the comodel record, then link it
                values[name] = fieldValue && this.store.load(field.relation, fieldValue);
            } else if (!X2MANY_TYPES.includes(field.type)) {
                values[name] = fieldValue;
            }
            // x2many defaults come as a list of commands: not supported yet
        }
        const record = this.store.create(this.resModel, values);
        this.createdAt = this.store.clock;
        return record;
    }
}

/**
 * Store values are records: modifiers expect ids, like on the server.
 *
 * @param {string} type
 * @param {any} value
 */
function toPyValue(type, value) {
    switch (type) {
        case "many2one":
            return value ? value.id : false;
        case "one2many":
        case "many2many":
            return (value || []).map((record) => record.id);
        default:
            return value ?? false;
    }
}

/**
 * Store definitions for the fields displayed by the view: the main model with
 * those fields, and each comodel with its `display_name`. All models are
 * tracked, so that local writes are kept apart from the server values.
 *
 * Relations are declared without inverse: the view does not edit x2many
 * fields, so there is nothing to keep in sync yet.
 *
 * @param {string} resModel
 * @param {Record<string, any>} fields
 * @param {string[]} fieldNames
 */
function buildStoreParams(resModel, fields, fieldNames) {
    /** @type {Record<string, { fields: Record<string, object> }>} */
    const definitions = { [resModel]: { fields: {} } };
    for (const name of fieldNames) {
        const { type, string, relation } = fields[name];
        definitions[resModel].fields[name] = { type, string, relation };
        if (relation) {
            definitions[relation] ||= { fields: {} };
            definitions[relation].fields.display_name = { type: "char" };
        }
    }
    const models = Object.keys(definitions).map(
        (name) =>
            class extends StoreModel {
                static _name = name;
                static _tracked = true;
            }
    );
    return { models, definitions };
}

/**
 * The `specification` of `web_read`, `web_save` and `onchange`: the displayed
 * fields, with the display name of related records.
 *
 * @param {Record<string, any>} fields
 * @param {string[]} fieldNames
 */
function buildSpecification(fields, fieldNames) {
    /** @type {Record<string, object>} */
    const specification = {};
    for (const name of fieldNames) {
        specification[name] = RELATIONAL_TYPES.includes(fields[name].type)
            ? { fields: { display_name: {} } }
            : {};
    }
    return specification;
}
