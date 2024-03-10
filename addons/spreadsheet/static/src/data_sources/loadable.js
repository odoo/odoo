/** @odoo-module */
// @ts-check

import { CellErrorType } from "@odoo/o-spreadsheet";
import { Deferred } from "@web/core/utils/concurrency";
import { LOADING_ERROR } from "./data_source";

/**
 * Generic class to represent a loadable value
 * that can be used as the value of a spreadsheet cell.
 * @template T
 */
export class Loadable {
    /**
     * @param {Promise<T>} [promise]
     */
    constructor(promise = new Promise(() => {})) {
        /** @type {"pending" | "resolved" | "rejected"} */
        this.status = "pending";

        /** @type {T | undefined} */
        this.value = undefined;

        /** @type {string | undefined} */
        this.errorMessage = undefined;

        const deferred = new Deferred();
        promise.then(deferred.resolve, deferred.reject);
        deferred
            .then((value) => {
                this.value = value;
                this.status = "resolved";
            })
            .catch((error) => {
                this.errorMessage = error?.message ?? error.toString();
                this.status = "rejected";
            });
        /** @type {Deferred} */
        this.deferred = deferred;
    }

    isResolved() {
        return this.status === "resolved";
    }

    isRejected() {
        return this.status === "rejected";
    }

    isPending() {
        return this.status === "pending";
    }

    /**
     * Transform the loadable into a value that can be used
     * as the result of a formula evaluation.
     * @param {string} [key] If the value is an object, the key of the property to return.
     * @returns {{ value: any, message?: string }}
     */
    toEvaluationValue(key) {
        switch (this.status) {
            case "resolved":
                if (key) {
                    return { value: this.value[key] };
                }
                return this;
            case "rejected":
                return { value: CellErrorType.GenericError, message: this.errorMessage };
            case "pending":
                return LOADING_ERROR;
        }
    }

    /**
     *
     * @param {string | Loadable<string>} format
     * @param {string} key
     */
    toEvaluationValueWithFormat(format, key) {
        if (!this.isResolved()) {
            return this.toEvaluationValue(key);
        }
        const formatIsLoadable = format instanceof Loadable;
        if (formatIsLoadable && !format.isResolved()) {
            return format.toEvaluationValue();
        }
        const value = key ? this.value[key] : this.value;
        return { value, format: formatIsLoadable ? format.value : format };
    }
}
