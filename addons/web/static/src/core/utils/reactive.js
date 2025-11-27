import { reactive } from "@odoo/owl";

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
