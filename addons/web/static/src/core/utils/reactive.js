import { reactive } from "@web/owl2/utils";

/**
 * This class should be used as a base when creating a class that is intended to
 * be used within the reactivity system, it avoids a specific class of bug where
 * callbacks that capture `this` declared in the constructor would escape the
 * reactivity system and prevent the observers from being notified:
 *
 * const bus = new EventBus();
 * class MyClass {
 *   constructor() {
 *     this.counter = 0;
 *     bus.addEventListener("change", () => this.counter++);
 *     //                                   ^ Will never be reactive, this mutation will be missed
 *   }
 * }
 * const myObj = reactive(new MyClass(bus), () => console.log(myObj.counter));
 * myObj.counter++; // logs 0;
 * bus.trigger("change"); // logs nothing!
 * myObj.counter++; // logs 2. counter == 1 was missed.
 */
export class Reactive {
    constructor() {
        return reactive(this);
    }
}

/**
 * Creates a side-effect that runs based on the content of reactive objects.
 * @template {object[]} T
 * @param {(...args: [...T]) => X} cb callback for the effect
 * @param {[...T]} deps the reactive objects that the effect depends on
 * @deprecated
 */
export function effect(cb, deps) {
    const reactiveDeps = reactive(deps, () => {
        cb(...reactiveDeps);
    });
    cb(...reactiveDeps);
}
