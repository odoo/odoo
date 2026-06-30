import { PyDate, PyDateTime, PyRelativeDelta, PyTime, PyTimeDelta } from "./py_date";

export class EvaluationError extends Error {}

/**
 * @param {any} iterable
 * @param {Function} func
 */
export function execOnIterable(iterable, func) {
    if (iterable === null) {
        // new Set(null) is fine in js but set(None) (-> new Set(null))
        // is not in Python
        throw new EvaluationError(`value not iterable`);
    }
    if (typeof iterable === "object" && !Array.isArray(iterable) && !(iterable instanceof Set)) {
        // dicts are considered as iterable in Python
        iterable = Object.keys(iterable);
    }
    if (typeof iterable?.[Symbol.iterator] !== "function") {
        // rules out undefined and other values not iterable
        throw new EvaluationError(`value not iterable`);
    }
    return func(iterable);
}

export const BUILTINS = {
    /**
     * @param {any} value
     * @returns {boolean}
     */
    bool(value) {
        switch (typeof value) {
            case "number":
                return value !== 0;
            case "string":
                return value !== "";
            case "boolean":
                return value;
            case "object":
                if (value === null || value === undefined) {
                    return false;
                }
                if (value.isTrue) {
                    return value.isTrue();
                }
                if (value instanceof Array) {
                    return !!value.length;
                }
                if (value instanceof Set) {
                    return !!value.size;
                }
                return Object.keys(value).length !== 0;
        }
        return true;
    },

    set(iterable) {
        if (arguments.length > 2) {
            // we always receive at least one argument: kwargs (return fnValue(...args, kwargs); in FunctionCall case)
            throw new EvaluationError(
                `set expected at most 1 argument, got (${arguments.length - 1}`
            );
        }
        return execOnIterable(iterable, (iterable) => {
            return new Set(iterable);
        });
    },

    max(...args) {
        // kwargs are not supported by Math.max.
        return Math.max(...args.slice(0, -1));
    },

    min(...args) {
        // kwargs are not supported by Math.min.
        return Math.min(...args.slice(0, -1));
    },

    time: {
        strftime(format) {
            return PyDateTime.now().strftime(format);
        },
    },

    context_today() {
        return PyDate.today();
    },

    get current_date() {
        // deprecated: today should be prefered
        return this.today;
    },

    get today() {
        return PyDate.today().strftime("%Y-%m-%d");
    },

    get now() {
        return PyDateTime.now().strftime("%Y-%m-%d %H:%M:%S");
    },

    datetime: {
        time: PyTime,
        timedelta: PyTimeDelta,
        datetime: PyDateTime,
        date: PyDate,
    },

    relativedelta: PyRelativeDelta,

    true: true,
    false: false,
};
