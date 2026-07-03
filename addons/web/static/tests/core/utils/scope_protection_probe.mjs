// Self-contained node harness for the scope-protection prototype.
//
//   node addons/web/static/tests/core/utils/scope_protection_probe.mjs
//
// It reimplements the CORE logic of scope_protection.js (the odoo module
// imports @odoo/owl, which does not resolve under plain node) against a mock
// Scope, and runs the experiments that decide the design:
//
//   D1  global then-patch does NOT intercept `await`         -> approach (B) fails
//   D2  global then-patch DOES intercept explicit `.then()`  -> (B) only helps .then
//   D3  thenable `protect()` DOES intercept `await`, guards at depth -> approach (A) works
//   D4  a foreign/native promise is untouched by protect()   -> (A) has no blast radius
//
// MOUNTED=1; dead = status > MOUNTED (CANCELLED=2 / DESTROYED=3).

const MOUNTED = 1;
const results = [];
const record = (name, pass, detail) => {
    results.push({ name, pass, detail });
    console.log(`${pass ? "PASS" : "FAIL"}  ${name}${detail ? `  -- ${detail}` : ""}`);
};

const makeAbortError = () => {
    const e = new Error("aborted: scope destroyed");
    e.name = "AbortError";
    return e;
};
const isDead = (s) => !!s && s.status > MOUNTED;

// A controllable "rpc": returns { promise, resolve } so we can settle it after
// deciding whether the scope is dead.
const deferred = () => {
    let resolve, reject;
    const promise = new Promise((res, rej) => {
        resolve = res;
        reject = rej;
    });
    return { promise, resolve, reject };
};

// ---------------------------------------------------------------------------
// (A) thenable protect()
// ---------------------------------------------------------------------------
function protect(real, scope, strategy = "throw") {
    const thenable = {
        then(onF, onR) {
            const settle = (isError, val) => {
                if (isDead(scope)) {
                    if (strategy === "pending") {
                        return new Promise(() => {});
                    }
                    const err = makeAbortError();
                    return onR ? onR(err) : Promise.reject(err);
                }
                if (isError) {
                    return onR ? onR(val) : Promise.reject(val);
                }
                return onF ? onF(val) : val;
            };
            return real.then(
                (v) => settle(false, v),
                (e) => settle(true, e)
            );
        },
    };
    return thenable;
}
const protectMethod = (scope, fn) => (...args) => protect(Promise.resolve(fn(...args)), scope);

// ---------------------------------------------------------------------------
// (B) ambient scope + global then-patch
// ---------------------------------------------------------------------------
let currentScope = null;
const runInScope = (scope, fn) => {
    const prev = currentScope;
    currentScope = scope;
    try {
        return fn();
    } finally {
        currentScope = prev;
    }
};
const origThen = Promise.prototype.then;
let patchFires = 0;
function installThenPatch() {
    // eslint-disable-next-line no-extend-native
    Promise.prototype.then = function (onF, onR) {
        const scope = currentScope;
        if (!scope) {
            return origThen.call(this, onF, onR);
        }
        const wrap = (cb) =>
            typeof cb === "function"
                ? (arg) => {
                      patchFires++;
                      if (isDead(scope)) {
                          throw makeAbortError();
                      }
                      return runInScope(scope, () => cb(arg));
                  }
                : cb;
        return origThen.call(this, wrap(onF), wrap(onR));
    };
}
function uninstallThenPatch() {
    // eslint-disable-next-line no-extend-native
    Promise.prototype.then = origThen;
}

// ===========================================================================
async function main() {
    // -------- D1: global then-patch vs native `await` ----------------------
    {
        installThenPatch();
        const scope = { status: MOUNTED };
        const d = deferred();
        let ranAfterAwait = false;
        const before = patchFires;
        const task = runInScope(scope, async () => {
            const v = await d.promise; // native await on native promise
            ranAfterAwait = true; // should be suppressed if patch worked
            return v;
        });
        scope.status = 3; // component destroyed while rpc in flight
        d.resolve("ok");
        await origThen.call(task, () => {}); // observe without re-patching
        uninstallThenPatch();
        // The point: the patch NEVER fired for the await, and the continuation
        // ran despite the dead scope. This is the known failure mode of (B).
        const patchSawAwait = patchFires > before;
        record(
            "D1 then-patch DID NOT protect awaited code (expected)",
            !patchSawAwait && ranAfterAwait, // "pass" = we successfully demonstrated the gap
            `patch fired for await: ${patchSawAwait}; continuation ran after destroy: ${ranAfterAwait}`
        );
    }

    // -------- D2: global then-patch vs explicit `.then()` ------------------
    {
        installThenPatch();
        const scope = { status: MOUNTED };
        const d = deferred();
        let cbRan = false;
        const chain = runInScope(scope, () =>
            d.promise.then((v) => {
                cbRan = true; // should be suppressed: scope dies before settle
                return v;
            })
        );
        scope.status = 3;
        d.resolve("ok");
        let aborted = false;
        try {
            await origThen.call(chain, (x) => x);
        } catch (e) {
            aborted = e.name === "AbortError";
        }
        uninstallThenPatch();
        record(
            "D2 then-patch intercepts explicit `.then()`",
            cbRan === false && aborted === true,
            `callback ran after destroy: ${cbRan}; threw AbortError: ${aborted}`
        );
    }

    // -------- D3: thenable protect() vs `await`, incl. depth ---------------
    {
        // 3a: alive -> resolves normally
        const scope = { status: MOUNTED };
        const d = deferred();
        const p = protect(d.promise, scope);
        d.resolve(123);
        let val;
        try {
            val = await p;
        } catch {
            /* ignore */
        }
        record("D3a protect() resolves when scope alive", val === 123, `value=${val}`);

        // 3b: destroyed mid-flight -> await throws AbortError
        const scope2 = { status: MOUNTED };
        const d2 = deferred();
        const p2 = protect(d2.promise, scope2);
        scope2.status = 3;
        d2.resolve("late");
        let abortName = null;
        let leaked = false;
        try {
            await p2;
            leaked = true;
        } catch (e) {
            abortName = e.name;
        }
        record(
            "D3b protect() throws AbortError on destroy (await)",
            abortName === "AbortError" && !leaked,
            `caught: ${abortName}`
        );

        // 3c: bound-at-injection guards a 3-deep await chain; destroy during rpc2
        const scope3 = { status: MOUNTED };
        const rpcs = [deferred(), deferred(), deferred()];
        let call = 0;
        const orm = protectMethod(scope3, () => rpcs[call++].promise);
        const reached = { after1: false, after2: false, after3: false };
        const chain = (async () => {
            await orm();
            reached.after1 = true;
            await orm(); // scope dies while this one is in flight
            reached.after2 = true;
            await orm();
            reached.after3 = true;
        })();
        // drive: settle rpc1, then destroy during rpc2, then settle the rest
        rpcs[0].resolve(1);
        await origThen.call(Promise.resolve(), () => {}); // let after1 run
        scope3.status = 3;
        rpcs[1].resolve(2);
        rpcs[2].resolve(3);
        let chainAbort = null;
        try {
            await chain;
        } catch (e) {
            chainAbort = e.name;
        }
        record(
            "D3c bound protect() stops an await chain at the death point",
            reached.after1 && !reached.after2 && !reached.after3 && chainAbort === "AbortError",
            `after1=${reached.after1} after2=${reached.after2} after3=${reached.after3} caught=${chainAbort}`
        );
    }

    // -------- D4: no blast radius on foreign/native promises ---------------
    {
        // A "library" native promise the app does not wrap: it must complete
        // normally even if some component nearby is dead. protect() never
        // touches it because it was never wrapped.
        const deadScope = { status: 3 };
        let libCompleted = false;
        const libPromise = Promise.resolve().then(() => {
            libCompleted = true; // library bookkeeping must run
            return "lib-done";
        });
        // We do NOT wrap libPromise in protect(); nothing installed globally now.
        const r = await libPromise;
        record(
            "D4 unwrapped foreign promise is unaffected (no blast radius)",
            libCompleted && r === "lib-done" && isDead(deadScope),
            `library completed: ${libCompleted}`
        );
    }

    // -------- summary ------------------------------------------------------
    console.log("\n--- summary ---");
    const passed = results.filter((r) => r.pass).length;
    console.log(`${passed}/${results.length} checks passed.`);
    console.log("D1: then-patch (B) is blind to `await` -> cannot protect most code.");
    console.log("D2: then-patch (B) only guards explicit `.then()` chains.");
    console.log("D3: thenable protect() (A) guards `await` at arbitrary depth.");
    console.log("D4: (A) touches only what flows through it -> no blast radius.");
}

main();
