// Verifies the PRODUCTION logic of use_async.js / rpc.toAsync / ORM.toAsync,
// mirrored here with mocks (the real modules import @odoo/owl + XHR).
//
//   node addons/web/static/tests/core/utils/scope_protection_use_async_probe.mjs

const MOUNTED = 1;
const isDead = (s) => s.status > MOUNTED;
const makeAbortError = () => {
    const e = new Error("aborted");
    e.name = "AbortError";
    return e;
};

// use_async.protect -- a plain derived promise (works natively with await)
const protect = (p, scope) =>
    Promise.resolve(p).then(
        (v) => {
            if (isDead(scope)) {
                throw makeAbortError();
            }
            return v;
        },
        (e) => {
            throw isDead(scope) ? makeAbortError() : e;
        }
    );

// a mock rpc with the same signal + abort wiring added to rpc._rpc
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
        promise.abort = () => {
            log.push("XHR aborted"); // the real one calls request.abort()
            if (!settled) {
                rejectFn(Object.assign(new Error("abort"), { name: "ConnectionAborted" }));
            }
        };
        promise._resolve = (v) => resolveFn(v); // test hook (stands in for the network)
        if (settings.signal) {
            const { signal } = settings;
            const onAbort = () => promise.abort();
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
            return Promise.reject(makeAbortError());
        }
        const real = rpc(url, params, { ...settings, signal: scope.abortSignal });
        const guarded = protect(real, scope);
        guarded.abort = real.abort;
        return guarded;
    };
}

// a scope whose abortSignal fires on destroy (faithful to owl: abort THEN mark
// destroyed, so the abort listener runs while status is still MOUNTED and the
// microtask reactions later observe DESTROYED)
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

const results = [];
const check = (name, pass, detail) => {
    results.push(pass);
    console.log(`${pass ? "PASS" : "FAIL"}  ${name}${detail ? `  -- ${detail}` : ""}`);
};

async function main() {
    // V1: normal completion (resolve the underlying real handle)
    {
        const log = [];
        const scope = makeScope();
        const base = makeRpc(log);
        let realHandle;
        const spyRpc = (u, p, s) => (realHandle = base(u, p, s));
        const rpc = toAsyncRpc(spyRpc, scope);
        const g = rpc("/x", {});
        realHandle._resolve(42);
        const v = await g;
        check("V1 normal completion", v === 42, `value=${v}`);
    }

    // V2: destroyed mid-flight -> XHR aborted AND await throws AbortError
    {
        const log = [];
        const scope = makeScope();
        const rpc = toAsyncRpc(makeRpc(log), scope);
        const g = rpc("/x", {});
        scope.destroy(); // aborts the signal
        let caught;
        try {
            await g;
        } catch (e) {
            caught = e.name;
        }
        check(
            "V2 destroy mid-flight",
            caught === "AbortError" && log.includes("XHR aborted"),
            `caught=${caught}, xhrAborted=${log.includes("XHR aborted")}`
        );
    }

    // V3: resolved-then-destroyed race -> continuation dropped (AbortError)
    {
        const log = [];
        const scope = makeScope();
        const base = makeRpc(log);
        let realHandle;
        const rpc = toAsyncRpc((u, p, s) => (realHandle = base(u, p, s)), scope);
        const g = rpc("/x", {});
        realHandle._resolve("data"); // response arrived...
        scope.destroy(); // ...but component destroyed before the continuation runs
        let caught;
        let leaked = false;
        try {
            await g;
            leaked = true;
        } catch (e) {
            caught = e.name;
        }
        check("V3 resolved-then-destroyed race", caught === "AbortError" && !leaked, `caught=${caught}`);
    }

    // V4: already dead before the call -> no request made, rejects immediately
    {
        const log = [];
        const scope = makeScope();
        scope.destroy();
        let made = false;
        const rpc = toAsyncRpc(() => {
            made = true;
            return makeRpc(log)("/x", {});
        }, scope);
        let caught;
        try {
            await rpc("/x", {});
        } catch (e) {
            caught = e.name;
        }
        check("V4 dead before call", caught === "AbortError" && !made, `caught=${caught}, requestMade=${made}`);
    }

    // V5: ORM rebind flows through silent / derived instances
    {
        const log = [];
        const scope = makeScope();
        const base = makeRpc(log);
        let lastHandle;
        const spyRpc = (u, p, s) => (lastHandle = base(u, p, s));

        // a tiny ORM mirroring the real one's shape
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

        // silent goes through the bound rpc too (inherited via prototype)
        const g = boundOrm.silent.read("res.partner", [1]);
        lastHandle._resolve([{ id: 1 }]);
        const recs = await g;
        check(
            "V5 ORM rebind (silent/derived)",
            Array.isArray(recs) && recs[0].id === 1,
            `got ${JSON.stringify(recs)}`
        );

        // and destroying the scope aborts an in-flight ORM request
        const g2 = boundOrm.read("res.partner", [2]);
        scope.destroy();
        let caught;
        try {
            await g2;
        } catch (e) {
            caught = e.name;
        }
        check(
            "V5b ORM in-flight cancelled on destroy",
            caught === "AbortError" && log.includes("XHR aborted"),
            `caught=${caught}`
        );
    }

    const passed = results.filter(Boolean).length;
    console.log(`\n${passed}/${results.length} checks passed.`);
}

main();
