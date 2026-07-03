// Why "globalThis.Promise = new Proxy(OriginalPromise, ...)" does NOT turn
// promises into thenables, and why `await` is unaffected.
//
//   node addons/web/static/tests/core/utils/scope_protection_why_proxy_fails.mjs

const OriginalPromise = globalThis.Promise;
const originalThen = OriginalPromise.prototype.then;

console.log("=== Truth 1: a Proxy on the CONSTRUCTOR does not make INSTANCES thenables ===");
globalThis.Promise = new Proxy(OriginalPromise, {
    construct(target, args, newTarget) {
        const instance = Reflect.construct(target, args, newTarget); // <-- a REAL promise
        instance.execContext = "stamped";
        return instance;
    },
});
const p = new Promise((res) => res(1)); // `Promise` here = the Proxy

console.log("  typeof globalThis.Promise :", typeof globalThis.Promise, "(the proxy is a constructor)");
console.log("  p instanceof OriginalPromise :", p instanceof OriginalPromise);
console.log("  proto(p) === %Promise.prototype% :", Object.getPrototypeOf(p) === OriginalPromise.prototype);
console.log("  p is a native promise, not a bare thenable. The proxy wrapped the");
console.log("  CONSTRUCTOR; it never wrapped the object `p`.\n");

// Instrument .then so we can see whether await ever routes through it.
let thenFired = 0;
// eslint-disable-next-line no-extend-native
OriginalPromise.prototype.then = function (a, b) {
    thenFired++;
    return originalThen.call(this, a, b);
};

async function truth2() {
    console.log("=== Truth 2: `await` dispatches on the awaited VALUE's type, not on globalThis.Promise ===");

    let before = thenFired;
    const v1 = await p; // p is a real native promise
    console.log(`  await (real promise) -> ${v1} | patched .then fired: ${thenFired > before}  (false = await bypassed it)`);

    before = thenFired;
    let thenableRan = false;
    const thenable = { then(res) { thenableRan = true; res(7); } }; // a genuine thenable
    const v2 = await thenable; // engine MUST call thenable.then
    console.log(`  await (thenable)     -> ${v2} | thenable.then ran: ${thenableRan}`);
    console.log("  Only a non-native thenable makes `await` call a .then method.");
    console.log("  `new Promise(...)` never produces that, whatever globalThis.Promise is.\n");
}

async function truth3() {
    // eslint-disable-next-line no-extend-native
    OriginalPromise.prototype.then = originalThen; // restore

    console.log("=== Truth 3: async functions ignore globalThis.Promise entirely ===");
    // Make the global Promise explode if anyone constructs through it.
    globalThis.Promise = class Broken {
        constructor() {
            throw new Error("global Promise was constructed!");
        }
    };
    async function f() {
        await 0; // internal await -> uses the %Promise% intrinsic
        return 42; // f's return promise -> also the intrinsic
    }
    try {
        const r = await OriginalPromise.resolve(f()); // drive it via the intrinsic
        console.log(`  async f() returned ${r} — the broken global Promise was NEVER touched.`);
        console.log("  => async/await is wired to the %Promise% intrinsic (fixed at engine init).");
        console.log("     Reassigning globalThis.Promise cannot change what `await` does.\n");
    } catch (e) {
        console.log("  unexpectedly threw:", e.message);
    }
    globalThis.Promise = OriginalPromise;

    console.log("--- conclusion ---");
    console.log("  The proxy makes the CONSTRUCTOR observable, not the INSTANCES thenable.");
    console.log("  await cares about the awaited value (native promise) and the %Promise%");
    console.log("  intrinsic (for async fns) — the proxy sits in neither path.");
}

await truth2();
await truth3();
