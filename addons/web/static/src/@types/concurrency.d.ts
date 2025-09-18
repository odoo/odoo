/**
 * Module augmentation for @web/core/utils/concurrency.
 *
 * The Deferred class uses a constructor return override (returns a Promise
 * with resolve/reject attached), which TypeScript cannot infer from the
 * class body alone.  This declaration augments the instance type.
 */
export {};

declare module "@web/core/utils/concurrency" {
    interface Deferred<T = unknown> extends Promise<T> {
        resolve(value?: T | PromiseLike<T>): void;
        reject(reason?: any): void;
    }
}
