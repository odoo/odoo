// Paste into a browser console (or run with node). Self-contained.
//
// Two independent flows (S1, S2). rpc() uses the "restore the scope, run the
// continuation, pop one microtick later" strategy. BOTH parts resolve in the
// SAME microtask batch (a cache hit / mock / already-resolved promise).
//
// The only difference between PART A and PART B is how the continuation is
// written: a synchronous `.then(cb)` vs `await`. That single difference decides
// whether the strategy works.

async function demo() {
    const stack = [];
    const cur = () => stack[stack.length - 1];

    // rpc: captures the ambient scope, re-pushes it right before completing,
    // pops one microtick later.
    function rpc() {
        const captured = cur();
        const real = Promise.resolve();
        return {
            then(onF, onR) {
                return real.then((v) => {
                    stack.push(captured);
                    const r = onF ? onF(v) : v; // the continuation
                    Promise.resolve().then(() => stack.pop()); // deferred pop
                    return r;
                }, onR);
            },
        };
    }

    // seed a flow's synchronous prefix; popped when it suspends at its first await
    function seeded(scope, fn) {
        stack.push(scope);
        try {
            return fn();
        } finally {
            stack.pop();
        }
    }

    const verdict = (seen) =>
        seen.S1 === "S1" && seen.S2 === "S2"
            ? "OK"
            : `WRONG (S1 saw ${seen.S1}, S2 saw ${seen.S2})`;

    // PART A: continuation is a SYNCHRONOUS .then callback (the colleague's model)
    {
        const seen = {};
        const a = seeded("S1", () => rpc().then(() => (seen.S1 = cur())));
        const b = seeded("S2", () => rpc().then(() => (seen.S2 = cur())));
        await Promise.all([a, b]);
        console.log("PART A  .then(callback):  ", verdict(seen));
    }

    stack.length = 0;

    // PART B: continuation is the code AFTER `await` (what real Odoo code uses)
    {
        const seen = {};
        const a = seeded("S1", () =>
            (async () => {
                await rpc();
                seen.S1 = cur();
            })()
        );
        const b = seeded("S2", () =>
            (async () => {
                await rpc();
                seen.S2 = cur();
            })()
        );
        await Promise.all([a, b]);
        console.log("PART B  async/await:      ", verdict(seen));
    }

    console.log(
        "\nSame rpc, same same-microtask-batch timing. The ONLY difference is\n" +
            ".then(cb) vs await:\n" +
            "  - a synchronous .then callback runs INSIDE the wrapper, right after its\n" +
            "    own push and before the sibling flow pushes -> it sees the right scope.\n" +
            "  - `await` resumes in a SEPARATE microtask, AFTER the sibling flow has\n" +
            "    already pushed its scope onto the shared stack -> it reads the wrong one.\n" +
            "Odoo code is async/await (PART B), so the microtick strategy conflates flows."
    );
}

demo();
