// Faithful reproduction of the colleague's cancellablePromise.js
// (commit 322f6ee) — global Promise Proxy + construct-trap stamping +
// patched Promise.prototype.then — tested against the styles that matter:
// explicit `.then()` chains vs native `async/await`.
//
//   node addons/web/static/tests/core/utils/scope_protection_colleague_probe.mjs
//
// `window` -> `globalThis` (same object in a browser). Everything is restored
// at the end so we don't poison the rest of the process.

const OriginalPromise = globalThis.Promise;
const originalThen = OriginalPromise.prototype.then;

const execContexts = [];
let thenPatchFires = 0; // instrumentation: did the patched .then run?

// --- his exact mechanism ----------------------------------------------------
globalThis.Promise = new Proxy(OriginalPromise, {
    construct(target, args, newTarget) {
        const instance = Reflect.construct(target, args, newTarget);
        instance.execContext = execContexts.at(-1); // stamp at construction
        return instance;
    },
    get(target, prop, receiver) {
        if (
            typeof target[prop] === "function" &&
            ["resolve", "reject", "all", "race", "allSettled", "any"].includes(prop)
        ) {
            return function (...args) {
                const newPromise = Reflect.apply(target[prop], target, args);
                newPromise.execContext = execContexts.at(-1);
                return newPromise;
            };
        }
        return Reflect.get(target, prop, receiver);
    },
});

// eslint-disable-next-line no-extend-native
OriginalPromise.prototype.then = function (onFulfilled, onRejected) {
    thenPatchFires++;
    return originalThen.call(
        this,
        onFulfilled ? (...args) => _exec(this.execContext, onFulfilled, args) : undefined,
        onRejected ? (...args) => _exec(this.execContext, onRejected, args) : undefined
    );
};

const _exec = (execContext, cb, args) => {
    if (execContext?.cancelled) {
        return; // leave pending
    }
    execContexts.push(execContext);
    const r = cb(...args);
    originalThen.call(
        OriginalPromise.resolve(),
        () => {
            execContexts.pop();
        },
        undefined
    );
    return r;
};

const effect = (cb) => {
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

// --- helpers ----------------------------------------------------------------
const tick = () => new OriginalPromise((res) => setTimeout(res, 5));
const results = [];
const record = (name, protectedOk, detail) => {
    results.push({ name, protectedOk });
    console.log(`${protectedOk ? "PROTECTED" : "NOT PROTECTED"}  ${name}${detail ? `  -- ${detail}` : ""}`);
};

async function main() {
    // S1: single explicit `.then`, promise CREATED inside the effect ---------
    {
        let resolve;
        let cbRan = false;
        const before = thenPatchFires;
        const e = effect(() => {
            const p = new Promise((res) => (resolve = res)); // stamped with context
            p.then(() => (cbRan = true));
        });
        e.cancel();
        resolve();
        await tick();
        record(
            "S1 explicit .then (promise born in effect)",
            cbRan === false,
            `cbRan=${cbRan}; patched then fired: ${thenPatchFires > before}`
        );
    }

    // S2: two-step chain .then().then() inside the effect --------------------
    {
        let resolve;
        let firstRan = false;
        let secondRan = false;
        const e = effect(() => {
            const p = new Promise((res) => (resolve = res));
            p.then(() => (firstRan = true)).then(() => (secondRan = true));
        });
        e.cancel();
        resolve();
        await tick();
        record(
            "S2 chained .then().then()  (2nd step)",
            firstRan === false && secondRan === false,
            `firstRan=${firstRan} secondRan=${secondRan}`
        );
    }

    // S3: native async/await inside the effect -------------------------------
    {
        let resolve;
        let afterAwait = false;
        const before = thenPatchFires;
        const e = effect(() => {
            (async () => {
                await new Promise((res) => (resolve = res)); // stamped, but await bypasses .then
                afterAwait = true;
            })();
        });
        e.cancel();
        resolve();
        await tick();
        record(
            "S3 native async/await",
            afterAwait === false,
            `afterAwait=${afterAwait}; patched then fired during await: ${thenPatchFires > before}`
        );
    }

    // S4: await, then a second await (chain of awaits) -----------------------
    {
        let r1, r2;
        let afterFirst = false;
        let afterSecond = false;
        const e = effect(() => {
            (async () => {
                await new Promise((res) => (r1 = res));
                afterFirst = true;
                await new Promise((res) => (r2 = res));
                afterSecond = true;
            })();
        });
        r1();
        await tick(); // let it reach the 2nd await
        e.cancel(); // cancel while 2nd await is in flight
        r2();
        await tick();
        record(
            "S4 second await after cancel",
            afterSecond === false,
            `afterFirst=${afterFirst} afterSecond=${afterSecond}`
        );
    }

    // --- summary ------------------------------------------------------------
    console.log("\n--- summary (colleague's mechanism) ---");
    for (const r of results) {
        console.log(`  ${r.protectedOk ? "✓ protects" : "✗ does NOT protect"}  ${r.name}`);
    }
    console.log(
        "\nThe question that matters: does it protect native async/await (S3/S4)?"
    );

    // restore globals
    // eslint-disable-next-line no-extend-native
    OriginalPromise.prototype.then = originalThen;
    globalThis.Promise = OriginalPromise;
}

main();
