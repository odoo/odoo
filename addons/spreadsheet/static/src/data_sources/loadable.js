import { CellErrorType } from "@odoo/o-spreadsheet";
/**
 * Generic class to represent a loadable value
 * that can be used as the value of a spreadsheet cell.
 * @template T
 * @property {Promise<T>}
 */
export class Loadable {
    static pending = /** @type {const} */ ("pending");
    static resolved = /** @type {const} */ ("resolved");
    static rejected = /** @type {const} */ ("rejected");

    static resolve(value) {
        return new Loadable(Promise.resolve(value));
    }

    static reject(error) {
        return new Loadable(Promise.reject(error));
    }

    /**
     * @template D
     * @param {Promise<T>} promise
     * @param {D} [defaultValue]
     */
    constructor(promise, defaultValue) {
        /** @type {"pending" | "resolved" | "rejected"} */
        this.status = Loadable.pending;

        /** @type {T | string} */
        this.value = defaultValue ?? "Loading..."; // TODO from the constant (translated)

        /** @type {string | undefined} */
        this.message = undefined;

        /** @type {Promise<T>} */
        this.promise = promise
            .then((value) => {
                this.value = value;
                this.status = Loadable.resolved;
                return value;
            })
            .catch((error) => {
                this.message = error?.message ?? error.toString();
                this.value = defaultValue ?? CellErrorType.GenericError;
                this.status = Loadable.rejected;
            });
    }

    /**
     * @template U
     * @param {(value: T) => U} fn
     * @returns {Loadable<U>}
     */
    map(fn) {
        return new Loadable(this.promise.then(fn));
    }

    /**
     * Defaults to the provided value if the promise is rejected or still pending
     *.
     * @template D
     * @param {D} defaultValue
     * @returns {Loadable<T | D>}
     */
    defaultsTo(defaultValue) {
        return new Loadable(this.promise, defaultValue);
    }
}
