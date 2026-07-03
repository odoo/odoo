// Does the colleague's "restore just before completion, pop one microtick later"
// strategy correctly propagate the scope to a SUBSEQUENT rpc — without
// interleaving bugs? Tested on top of a thenable rpc (so `await` is intercepted).
//
//   node addons/web/static/tests/core/utils/scope_protection_deferred_pop_probe.mjs
//
// Faithful to cancellablePromise.js _exec: push context, run callback (which
// resolves the await -> schedules the resume), then schedule pop via
// Promise.resolve().then(pop) so it fires AFTER the resume microtask.

const OP = Promise;
let execContexts = [];
const currentScope = () => execContexts.at(-1);

const deferred = () => {
    let resolve, reject;
    const promise = new OP((res, rej) => {
        resolve = res;
        reject = rej;
    });
    return { promise, resolve, reject };
};
const macrotask = () => new OP((res) => setTimeout(res, 0));

// rpc: a thenable bound to nothing; it captures the ambient scope at call time,
// re-pushes it right before completing, and pops one microtick later.
let rpcSeq = 0;
const captures = []; // { id, captured, expected }
function rpc(real, expected) {
    const id = ++rpcSeq;
    const captured = currentScope();
    captures.push({ id, captured, expected });
    return {
        then(onF, onR) {
            return real.then(
                (v) => {
                    execContexts.push(captured); // restore just before completion
                    const r = onF ? onF(v) : v; // resolves the await -> schedules resume
                    OP.resolve().then(() => execContexts.pop()); // pop after a microtick
                    return r;
                },
                (e) => (onR ? onR(e) : OP.reject(e))
            );
        },
    };
}

// seed the scope for a handler's synchronous prefix (~ runInScope in
// mainEventHandler); popped as soon as the handler suspends at its first await.
function seedAndRun(scope, asyncFn) {
    execContexts.push(scope);
    try {
        return asyncFn();
    } finally {
        execContexts.pop();
    }
}

function reset() {
    execContexts = [];
    captures.length = 0;
    rpcSeq = 0;
}
function report(name) {
    const bad = captures.filter((c) => c.captured !== c.expected);
    const line = captures
        .map((c) => `rpc#${c.id}:${c.captured === c.expected ? "ok" : `${c.captured}!=${c.expected}`}`)
        .join(" ");
    console.log(`${bad.length ? "FAIL" : "PASS"}  ${name}\n      ${line}`);
    reset();
}

async function main() {
    // T1: single chain, sequential rpc -> rpc, MACROtask resolution (network-like)
    {
        const d1 = deferred();
        const d2 = deferred();
        const done = seedAndRun("S", async () => {
            await rpc(d1.promise, "S");
            await rpc(d2.promise, "S"); // must still capture S
        });
        d1.resolve();
        await macrotask();
        d2.resolve();
        await done;
        report("T1 single chain, rpc->rpc (macrotask gaps)");
    }

    // T2: single chain, THREE sequential rpcs, microtask resolution
    {
        const ds = [deferred(), deferred(), deferred()];
        const done = seedAndRun("S", async () => {
            await rpc(ds[0].promise, "S");
            await rpc(ds[1].promise, "S");
            await rpc(ds[2].promise, "S");
        });
        ds.forEach((d) => d.resolve());
        await done;
        report("T2 single chain, rpc->rpc->rpc (microtask)");
    }

    // T3: intervening NON-rpc await between two rpcs
    {
        const d1 = deferred();
        const d2 = deferred();
        const done = seedAndRun("S", async () => {
            await rpc(d1.promise, "S");
            await OP.resolve(); // a plain microtask await (e.g. a local helper)
            await rpc(d2.promise, "S"); // does it still see S?
        });
        d1.resolve();
        await macrotask();
        d2.resolve();
        await done;
        report("T3 rpc -> await Promise.resolve() -> rpc");
    }

    // T4: two concurrent chains, resolutions in SEPARATE macrotasks (real network)
    {
        const a1 = deferred();
        const a2 = deferred();
        const b1 = deferred();
        const b2 = deferred();
        const hA = seedAndRun("S1", async () => {
            await rpc(a1.promise, "S1");
            await rpc(a2.promise, "S1");
        });
        const hB = seedAndRun("S2", async () => {
            await rpc(b1.promise, "S2");
            await rpc(b2.promise, "S2");
        });
        // stagger each resolution into its own macrotask
        a1.resolve();
        await macrotask();
        b1.resolve();
        await macrotask();
        a2.resolve();
        await macrotask();
        b2.resolve();
        await OP.all([hA, hB]);
        report("T4 two chains, separate macrotasks (staggered)");
    }

    // T5: two concurrent chains, resolutions in the SAME microtask batch (cache/Promise.all-like)
    {
        const a1 = deferred();
        const a2 = deferred();
        const b1 = deferred();
        const b2 = deferred();
        const hA = seedAndRun("S1", async () => {
            await rpc(a1.promise, "S1");
            await rpc(a2.promise, "S1");
        });
        const hB = seedAndRun("S2", async () => {
            await rpc(b1.promise, "S2");
            await rpc(b2.promise, "S2");
        });
        // resolve everything back-to-back (no macrotask gaps) -> microtasks interleave
        a1.resolve();
        b1.resolve();
        a2.resolve();
        b2.resolve();
        await OP.all([hA, hB]);
        report("T5 two chains, same microtask batch (no gaps)");
    }

    // T6: concurrency inside ONE handler via Promise.all
    {
        const d1 = deferred();
        const d2 = deferred();
        const done = seedAndRun("S", async () => {
            await OP.all([rpc(d1.promise, "S"), rpc(d2.promise, "S")]);
            await rpc(deferred_resolved(), "S"); // a follow-up rpc after the all()
        });
        function deferred_resolved() {
            return OP.resolve();
        }
        d1.resolve();
        d2.resolve();
        await done;
        report("T6 Promise.all([rpc,rpc]) then rpc (same handler)");
    }

    console.log(
        "\nLegend: PASS = every rpc captured the scope it should. FAIL = at least one\n" +
            "rpc captured the wrong scope (or undefined) => protection would be misapplied."
    );
}

main();
