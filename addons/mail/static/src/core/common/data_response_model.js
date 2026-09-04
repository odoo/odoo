import { fields, Record } from "@mail/model/export";

/**
 * @template T
 * @typedef {{
 *   [K in keyof T as T[K] extends Function ? never : K]: T[K]
 * }} InstanceFields
 */

/**
 * This class represents a specific and unique request coming from the client to the server, and it
 * also holds the corresponding response coming from the server.
 * It is useful when batching requests together to determine which data to return for a specific
 * request. It basically does the un-batching by referencing the given id. The rest of the data
 * being grouped together in the store, flattened and with no duplicate records/fields, no matter
 * how many requests are returning the same data.
 * Instances of the class are created by the fetch method on each call, and they are deleted once
 * they are resolved with their data. This class should not be used directly under typical use.
 */
export class DataResponse extends Record {
    static _lastId = 0;

    /** @returns {import("models").DataResponse} */
    static createRequest() {
        return this.insert({ id: ++this._lastId });
    }

    /** @type {number} */
    id;
    setup() {
        super.setup();
        this.onChange(
            () => [this._resolve],
            function onChangeResolve(_resolve) {
                if (_resolve) {
                    // A record holds its fields in signals, so it does not
                    // spread, and the delete below empties its relations.
                    const data = {};
                    for (const name of this.Model._.fields.keys()) {
                        const value = this[name];
                        data[name] = Array.isArray(value) ? [...value] : value;
                    }
                    this._resultResolvers.resolve(data);
                    this.delete();
                }
            }
        );
    }
    /**
     * When set to true, this data request is resolved as soon as its RPC returns, even if there was
     * no actual data for this request inside it. This is useful for fetch request that only fills
     * the store but does not need to wait any particular value.
     */
    _autoResolve = false;
    /**
     * When set to true, resolves this data request with the current values of the fields as data,
     * and then deletes the data request.
     *
     * @type {boolean}
     */
    _resolve = undefined;
    /**
     * Promise that is resolved with the data when the data request is complete.
     * @type {PromiseWithResolvers<InstanceFields<DataResponse>>}
     */
    _resultResolvers = Promise.withResolvers();
    /*
     * Fields are contextual to each data request. They are generically added here to benefit from
     * fields behavior as well as auto-complete, but their meaning depends on each data request.
     * Existing fields defined here should be used in new data requests if they fit the purpose, and
     * other fields can be added if necessary.
     */
    attachments = fields.Many("ir.attachment");
    channel = fields.One("discuss.channel");
    channels = fields.Many("discuss.channel");
    /** @type {number} */
    count;
    /** @type {boolean} */
    is_fully_loaded;
    message = fields.One("mail.message");
    messages = fields.Many("mail.message");
    partners = fields.Many("res.partner");
}

DataResponse.register();
