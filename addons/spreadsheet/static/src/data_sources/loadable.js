import { CellErrorType } from "@odoo/o-spreadsheet";
/**
 * Generic class to represent a loadable value
 * that can be used as the value of a spreadsheet cell.
 * @template T
 * @property {Promise<T>}
 */
export class Loadable {
    /**
     * @param {Promise<T>} promise
     */
    constructor(promise) {
        /** @type {"pending" | "resolved" | "rejected"} */
        this.status = "pending";

        /** @type {T | string} */
        this.value = "Loading..."; // TODO from the constant (translated)

        /** @type {string | undefined} */
        this.message = undefined;

        /** @type {Promise<T>} */
        this.promise = promise
            .then((value) => {
                this.value = value;
                this.status = "resolved";
                return value;
            })
            .catch((error) => {
                this.message = error.message;
                this.value = CellErrorType.GenericError;
                this.status = "rejected";
            });
    }
}
