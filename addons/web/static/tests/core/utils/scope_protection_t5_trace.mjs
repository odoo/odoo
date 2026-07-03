// Instrumented trace of T5: two concurrent chains whose rpcs resolve in the
// same microtask batch. Prints the shared context stack at every step so the
// conflation is visible.
//
//   node addons/web/static/tests/core/utils/scope_protection_t5_trace.mjs

const OP = Promise;
let execContexts = [];
const stack = () => `[${execContexts.join(", ")}]`;
const currentScope = () => execContexts.at(-1);
const log = (msg) => console.log(msg.padEnd(46), "stack =", stack());

const deferred = () => {
    let resolve;
    const promise = new OP((res) => (resolve = res));
    return { promise, resolve };
};

function rpc(real, label) {
    const captured = currentScope();
    console.log(`  ${label} called -> captures ${captured}`);
    return {
        then(onF, onR) {
            return real.then((v) => {
                execContexts.push(captured);
                log(`  ${label} completing: push ${captured}`);
                const r = onF ? onF(v) : v; // resolves the await -> schedules resume
                OP.resolve().then(() => {
                    execContexts.pop();
                    log(`  ${label} deferred pop`);
                });
                return r;
            }, onR);
        },
    };
}

function seedAndRun(scope, fn) {
    execContexts.push(scope);
    try {
        return fn();
    } finally {
        execContexts.pop();
    }
}

async function main() {
    const a1 = deferred();
    const a2 = deferred();
    const b1 = deferred();
    const b2 = deferred();

    const hA = seedAndRun("S1", async () => {
        await rpc(a1.promise, "A.rpc1(S1)");
        log(`  A resumes after rpc1: sees ${currentScope()}`);
        await rpc(a2.promise, "A.rpc2(S1)"); // EXPECT captures S1
    });
    const hB = seedAndRun("S2", async () => {
        await rpc(b1.promise, "B.rpc1(S2)");
        log(`  B resumes after rpc1: sees ${currentScope()}`);
        await rpc(b2.promise, "B.rpc2(S2)"); // EXPECT captures S2
    });

    // same microtask batch: no macrotask gap between completions
    a1.resolve();
    b1.resolve();
    a2.resolve();
    b2.resolve();
    await OP.all([hA, hB]);

    console.log("\nThe stack held [S1, S2] at once -> A's resume read the TOP (S2),");
    console.log("not its own S1. One shared LIFO stack cannot represent two");
    console.log("concurrent async chains.");
}

main();
