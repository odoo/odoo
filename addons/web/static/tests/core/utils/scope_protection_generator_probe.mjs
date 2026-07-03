// Generators for rpc-consuming flows: a per-chain runner holds the scope in its
// CLOSURE and checks it before each resume. No shared ambient stack => no T5 race.
//
//   node addons/web/static/tests/core/utils/scope_protection_generator_probe.mjs

const OP = Promise;
const MOUNTED = 1;
const isDead = (s) => s.status > MOUNTED;
const makeAbortError = () => {
    const e = new Error("aborted");
    e.name = "AbortError";
    return e;
};

// A scope-aware driver. `scope` lives in this closure — nothing is shared
// between concurrent runScoped() calls, so there is nothing to conflate.
// rpc() itself does NOT need to be scope-aware: the runner attributes the scope.
async function runScoped(scope, genFn, ...args) {
    const gen = genFn(...args);
    let input;
    let threw = false;
    while (true) {
        if (isDead(scope)) {
            gen.return(); // run the generator's finally blocks, then stop
            throw makeAbortError();
        }
        const step = threw ? gen.throw(input) : gen.next(input);
        if (step.done) {
            return step.value;
        }
        try {
            input = await step.value; // perform the yielded effect (an rpc promise)
            threw = false;
        } catch (e) {
            input = e;
            threw = true;
        }
        // loop: re-check scope BEFORE handing the result back to the generator
    }
}

const deferred = () => {
    let resolve;
    const promise = new OP((res) => (resolve = res));
    return { promise, resolve };
};

async function main() {
    // Two concurrent flows, different scopes, rpcs resolve in the SAME microtask
    // batch (the exact T5 setup). We destroy S1 between its two rpcs.
    const scopeA = { status: MOUNTED };
    const scopeB = { status: MOUNTED };
    const a1 = deferred();
    const a2 = deferred();
    const b1 = deferred();
    const b2 = deferred();
    const trace = [];

    function* flow(name, r1, r2) {
        try {
            yield r1.promise;
            trace.push(`${name}: after rpc1`);
            yield r2.promise; // A must NOT get here (scope destroyed); B must
            trace.push(`${name}: after rpc2`);
            return `${name}-done`;
        } finally {
            trace.push(`${name}: finally (cleanup ran)`);
        }
    }

    const runA = runScoped(scopeA, flow, "A", a1, a2).catch((e) => `A-${e.name}`);
    const runB = runScoped(scopeB, flow, "B", b1, b2).then((v) => v);

    // resolve rpc1 of both in the same batch
    a1.resolve();
    b1.resolve();
    await OP.resolve(); // let both flows advance past rpc1
    await OP.resolve();

    // destroy A's scope; resolve the remaining rpcs in the same batch as well
    scopeA.status = 3;
    a2.resolve();
    b2.resolve();

    const [resA, resB] = await OP.all([runA, runB]);

    console.log("trace:");
    for (const t of trace) {
        console.log("  " + t);
    }
    console.log(`\nA result: ${resA}   (expect A-AbortError, no "after rpc2")`);
    console.log(`B result: ${resB}   (expect B-done)`);

    const aStopped = !trace.includes("A: after rpc2") && trace.includes("A: finally (cleanup ran)");
    const bComplete = trace.includes("B: after rpc2") && resB === "B-done";
    console.log(
        `\n${aStopped && bComplete ? "PASS" : "FAIL"}: A stopped+cleaned at the death point; ` +
            `B completed. No conflation, no race — each runner held its own scope.`
    );
}

main();
