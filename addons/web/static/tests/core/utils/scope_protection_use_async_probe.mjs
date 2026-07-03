// Verifies the PRODUCTION logic of use_async.js / rpc.toAsync / ORM.toAsync,
// mirrored here with mocks (the real modules import @odoo/owl + XHR).
// Semantics: a destroyed scope DROPS the continuation (promise never settles),
// and the in-flight request is cancelled.
//
//   node addons/web/static/tests/core/utils/scope_protection_use_async_probe.mjs

const MOUNTED = 1;
const isDead = (s) => s.status > MOUNTED;
const dropped = () => new Promise(() => {}); // never settles

// use_async.protect
const protect = (p, scope) => Promise.resolve(p).then((r) => (isDead(scope) ? dropped() : r));

// mock rpc with the same signal + abort wiring added to rpc._rpc
function makeRpc(log) {
    return function rpc(url, params, settings = {}) {
        let resolveFn;
        let rejectFn;
        let settled = false;
        const promise = new Promise((res, rej) => {
            resolveFn = (v) => {
                settled = true;
                res(v);
            };
            rejectFn = (e) => {
                settled = true;
                rej(e);
            };
        });
        promise.abort = (rejectError = true) => {
            log.push("XHR aborted");
            if (rejectError && !settled) {
                rejectFn(Object.assign(new Error("abort"), { name: "ConnectionAborted" }));
            }
        };
        promise._resolve = (v) => resolveFn(v); // test hook (stands in for the network)
        if (settings.signal) {
            const { signal } = settings;
            const onAbort = () => promise.abort(false); // cancel, don't reject
            if (signal.aborted) {
                onAbort();
            } else {
                signal.addEventListener("abort", onAbort);
                const stop = () => signal.removeEventListener("abort", onAbort);
                promise.then(stop, stop);
            }
        }
        return promise;
    };
}

// rpc.toAsync
function toAsyncRpc(rpc, scope) {
    return function (url, params, settings = {}) {
        if (isDead(scope)) {
            return dropped();
        }
        const real = rpc(url, params, { ...settings, signal: scope.abortSignal });
        const guarded = protect(real, scope);
        guarded.abort = real.abort;
        return guarded;
    };
}

// scope whose abortSignal fires on destroy (owl: abort THEN mark destroyed)
function makeScope() {
    const ctrl = new AbortController();
    return {
        status: MOUNTED,
        get abortSignal() {
            return ctrl.signal;
        },
        destroy() {
            ctrl.abort();
            this.status = 3;
        },
    };
}

// does `p` settle within a few ticks?
async function settles(p) {
    const PENDING = Symbol("pending");
    const timer = new Promise((res) => setTimeout(() => res(PENDING), 10));
    const r = await Promise.race([p.then(() => "ok", () => "err"), timer]);
    return r !== PENDING;
}

const results = [];
const check = (name, pass, detail) => {
    results.push(pass);
    console.log(`${pass ? "PASS" : "FAIL"}  ${name}${detail ? `  -- ${detail}` : ""}`);
};

async function main() {
    // V1: normal completion resolves with the value
    {
        const log = [];
        const scope = makeScope();
        const base = makeRpc(log);
        let realHandle;
        const rpc = toAsyncRpc((u, p, s) => (realHandle = base(u, p, s)), scope);
        const g = rpc("/x", {});
        realHandle._resolve(42);
        const v = await g;
        check("V1 normal completion", v === 42, `value=${v}`);
    }

    // V2: destroyed mid-flight -> XHR aborted AND continuation dropped (never settles)
    {
        const log = [];
        const scope = makeScope();
        const rpc = toAsyncRpc(makeRpc(log), scope);
        const g = rpc("/x", {});
        scope.destroy();
        const didSettle = await settles(g);
        check(
            "V2 destroy mid-flight",
            !didSettle && log.includes("XHR aborted"),
            `settled=${didSettle}, xhrAborted=${log.includes("XHR aborted")}`
        );
    }

    // V3: resolved-then-destroyed race -> continuation dropped
    {
        const log = [];
        const scope = makeScope();
        const base = makeRpc(log);
        let realHandle;
        const rpc = toAsyncRpc((u, p, s) => (realHandle = base(u, p, s)), scope);
        const g = rpc("/x", {});
        realHandle._resolve("data"); // response arrived...
        scope.destroy(); // ...but component destroyed before the continuation runs
        const didSettle = await settles(g);
        check("V3 resolved-then-destroyed race", !didSettle, `settled=${didSettle}`);
    }

    // V4: already dead before the call -> no request made, continuation dropped
    {
        const log = [];
        const scope = makeScope();
        scope.destroy();
        let made = false;
        const rpc = toAsyncRpc(() => {
            made = true;
            return makeRpc(log)("/x", {});
        }, scope);
        const didSettle = await settles(rpc("/x", {}));
        check("V4 dead before call", !didSettle && !made, `settled=${didSettle}, requestMade=${made}`);
    }

    // V5: ORM rebind flows through silent / derived instances
    {
        const log = [];
        const scope = makeScope();
        const base = makeRpc(log);
        let lastHandle;
        const spyRpc = (u, p, s) => (lastHandle = base(u, p, s));
        const orm = {
            rpc: spyRpc,
            _silent: false,
            get silent() {
                return Object.assign(Object.create(this), { _silent: true });
            },
            call(model, method) {
                return this.rpc(`/call/${model}/${method}`, { silent: this._silent });
            },
            read(model, ids) {
                return this.call(model, "read");
            },
        };
        // ORM.toAsync: rebind the single this.rpc choke point
        const boundOrm = Object.assign(Object.create(orm), { rpc: toAsyncRpc(orm.rpc, scope) });

        const g = boundOrm.silent.read("res.partner", [1]);
        lastHandle._resolve([{ id: 1 }]);
        const recs = await g;
        check("V5 ORM rebind (silent/derived)", Array.isArray(recs) && recs[0].id === 1, `got ${JSON.stringify(recs)}`);

        const g2 = boundOrm.read("res.partner", [2]);
        scope.destroy();
        const didSettle = await settles(g2);
        check(
            "V5b ORM in-flight cancelled on destroy",
            !didSettle && log.includes("XHR aborted"),
            `settled=${didSettle}, xhrAborted=${log.includes("XHR aborted")}`
        );
    }

    const passed = results.filter(Boolean).length;
    console.log(`\n${passed}/${results.length} checks passed.`);
}

main();
