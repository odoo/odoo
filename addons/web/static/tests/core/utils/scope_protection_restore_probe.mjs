// Can a thenable rpc() "restore" the ambient scope AFTER `await`, so the
// continuation (and the next bare rpc()) sees it again?
//
//   node addons/web/static/tests/core/utils/scope_protection_restore_probe.mjs
//
// A: single chain in isolation  -> the "leave the global set" trick appears to work
// B: TWO concurrent chains       -> it races; a chain sees the WRONG scope
// C: engine-level (AsyncLocalStorage / the future AsyncContext) -> correct, even concurrent

import { AsyncLocalStorage } from "node:async_hooks";

const OP = Promise; // native

// --- userland ambient variable + a thenable rpc that captures & "restores" ---
let currentScope = null;

// a controllable rpc: real work resolves after `delayTicks` microtasks
function rpc(value) {
    const captured = currentScope; // capture ambient scope at call time
    const real = OP.resolve(value);
    return {
        then(onF, onR) {
            return real.then(
                (v) => {
                    currentScope = captured; // "restore" the scope before resuming
                    return onF ? onF(v) : v; // onF === the await's internal resolve
                },
                onR
            );
        },
    };
}

async function A() {
    console.log("=== A: single chain (isolation) ===");
    currentScope = "S";
    const a = await rpc(1);
    console.log(`  after await: currentScope = ${currentScope} (want "S")  a=${a}`);
    console.log(currentScope === "S" ? "  -> looks like it works...\n" : "  -> broken\n");
    currentScope = null;
}

async function B() {
    console.log("=== B: two concurrent chains (the real test) ===");
    const seen = {};
    async function handler(scope, v) {
        currentScope = scope;
        await rpc(v); // rpc captured `scope`; tries to restore it after await
        seen[scope] = currentScope; // what the continuation actually observes
    }
    await OP.all([handler("S1", 1), handler("S2", 2)]);
    console.log(`  handler S1 saw: ${seen.S1} (want "S1")`);
    console.log(`  handler S2 saw: ${seen.S2} (want "S2")`);
    const ok = seen.S1 === "S1" && seen.S2 === "S2";
    console.log(
        ok
            ? "  -> correct (got lucky with ordering)\n"
            : "  -> WRONG: the shared global was clobbered between resolve and resume.\n"
    );
    currentScope = null;
}

async function C() {
    console.log("=== C: engine-level context (AsyncLocalStorage ~ future AsyncContext) ===");
    const als = new AsyncLocalStorage();
    const seen = {};
    async function handler(scope, v) {
        return als.run(scope, async () => {
            await OP.resolve(v); // plain native await, no thenable tricks
            await OP.resolve(v); // and a second await, to show depth
            seen[scope] = als.getStore();
        });
    }
    await OP.all([handler("S1", 1), handler("S2", 2)]);
    console.log(`  handler S1 saw: ${seen.S1} (want "S1")`);
    console.log(`  handler S2 saw: ${seen.S2} (want "S2")`);
    const ok = seen.S1 === "S1" && seen.S2 === "S2";
    console.log(
        ok
            ? "  -> correct, across await AND concurrency. This is what AsyncContext will bring to browsers.\n"
            : "  -> unexpectedly wrong\n"
    );
}

await A();
await B();
await C();

console.log("--- verdict ---");
console.log("Capturing the scope at call time: fine.");
console.log("Restoring ambient scope AFTER a native await via a shared variable:");
console.log("races across concurrent async chains (B). Only engine-level context (C) is correct.");
