// You can wrap it in a helper function
function isGeneratorFunction(func) {
    return typeof func === "function" && func.constructor.name === "GeneratorFunction";
}

const stack = [];

// Get the prototype of a generator function's return value
const GeneratorPrototype = Object.getPrototypeOf(Object.getPrototypeOf(function* () {}.prototype));

function isGeneratorIteratorByPrototype(obj) {
    return Object.getPrototypeOf(obj) === GeneratorPrototype;
}

export function cancelablePromise(generatorFn) {
    let isCancel = false;
    let called = false;

    const ctx = { children: [] };

    const next = (currentGen, lastResult, finish) => {
        if (isCancel) {
            return;
        }
        let genResult;
        do {
            genResult = currentGen.next(lastResult);
            lastResult = genResult.value;
            if (genResult.value instanceof Promise) {
                genResult.value.then((r) => next(currentGen, r, finish));
                return;
            }
            if (isGeneratorFunction(lastResult)) {
                const subGen = lastResult();
                next(subGen, undefined, (r) => {
                    next(currentGen, r, finish);
                });
                return;
            }
            if (isGeneratorIteratorByPrototype(lastResult)) {
                next(lastResult, undefined, (r) => {
                    next(currentGen, r, finish);
                });
                return;
            }
            if (genResult.done) {
                finish?.(lastResult);
                return;
            }
        } while (!genResult.done);
    };
    const gen = generatorFn();

    return {
        get isCancel() {
            return isCancel;
        },
        call() {
            if (called) {
                return;
            }
            called = true;
            next(gen, undefined, () => {
                gen.return();
            });
        },
        cancel() {
            isCancel = true;
            gen.return();
        },
    };
}

// await test(function* () {
//   let i = 1;
//   const a = yield 'aValue';
//   console.log('a', a);
//   const x = yield timeout(i, 1000);
//   console.log('x', x);
//   const y = yield timeout(2, 1000);
//   console.log('y', y);
// });

// await test();
