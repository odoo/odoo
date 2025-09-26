// 1. Store a reference to the original Promise constructor
// const OriginalPromise = Promise;

import { on } from "@odoo/hoot-dom";
import { patch } from "./patch";

// 2. Define your custom Promise wrapper

const execContexts = [];

const OriginalPromise = Promise;
// export class CancellablePromise extends Promise {
// execContext = execContexts.at(-1);
// // setup(executor) {
// //     this.super(executor);
// // }
// then(onFulfilled, onRejected) {
//     // return super.then(onFulfilled, onRejected);
//     return super.then(
//         // onFulfilled ? (...args) => _exec(this.execContext, onFulfilled, args) : undefined,
//         onFulfilled ? (...args) => _exec(this.execContext, onFulfilled, args) : undefined,
//         onRejected ? (...args) => _exec(this.execContext, onRejected, args) : undefined
//     );
// }
// }

const originalThen = Promise.prototype.then;

const PromiseConstructor = Promise.prototype.constructor;
Promise.prototype.constructor = function (...args) {
    const instance = Reflect.construct(PromiseConstructor, args, Promise);
    console.warn("promise constructor");
    instance.execContext = execContexts.at(-1);
    return instance;
};

window.Promise = new Proxy(OriginalPromise, {
    construct(target, args, newTarget) {
        const instance = Reflect.construct(target, args, newTarget);
        instance.execContext = execContexts.at(-1); // Add context
        // console.warn("Proxied 'new Promise()'"); // For debugging
        return instance;
    },
    get(target, prop, receiver) {
        if (
            typeof target[prop] === "function" &&
            ["resolve", "reject", "all", "race", "allSettled", "any"].includes(prop)
        ) {
            return function (...args) {
                const newPromise = Reflect.apply(target[prop], target, args);
                newPromise.execContext = execContexts.at(-1); // Add context
                // console.warn(`Proxied 'Promise.${prop}()'`); // For debugging
                return newPromise;
            };
        }
        return Reflect.get(target, prop, receiver);
    },
});

Promise.prototype.then = function (onFulfilled, onRejected) {
    // if (!_compute) {
    // return originalThen.call(this, onFulfilled, onRejected);
    // }
    return originalThen.call(
        this,
        onFulfilled ? (...args) => _exec(this.execContext, onFulfilled, args) : undefined,
        onRejected ? (...args) => _exec(this.execContext, onRejected, args) : undefined
    );
};

// window.Promise = CancellablePromise;

export const _exec = (execContext, cb, args) => {
    if (execContext?.cancelled) {
        return;
    }
    execContexts.push(execContext);
    const r = cb(...args);
    originalThen.call(
        Promise.resolve(),
        () => {
            execContexts.pop();
        },
        undefined
    );
    // OriginalPromise.resolve().then(
    //     () => {
    //         execContexts.pop();
    //     },
    //     undefined,
    //     false
    // );
    return r;
};
export const effect = (cb) => {
    const context = { cancelled: false };
    execContexts.push(context);
    cb();
    execContexts.pop();
    return {
        cancel: () => (context.cancelled = true),
        get isCancel() {
            return context.cancelled;
        },
    };
};

// await test(function* () {
//   let i = 1;
//   const a = yield 'aValue';
//   console.log('a', a);
//   const x = yield timeout(i, 1000);
//   console.log('x', x);
//   const y = yield timeout(2, 1000);
//   console.log('y', y);
// });

// await test();
