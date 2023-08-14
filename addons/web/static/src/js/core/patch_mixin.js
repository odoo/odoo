odoo.define("web.patchMixin", function () {
    "use strict";

    /**
     * This module defines and exports the 'patchMixin' function. This function
     * returns a 'monkey-patchable' version of the ES6 Class given in arguments.
     *
     *    const patchMixin = require('web.patchMixin');
     *    class MyClass {
     *        print() {
     *            console.log('MyClass');
     *        }
     *    }
     *    const MyPatchedClass = patchMixin(MyClass);
     *
     *
     * A patchable class has a 'patch' function, allowing to define a patch:
     *
     *    MyPatchedClass.patch("module_name.key", T =>
     *        class extends T {
     *            print() {
     *                console.log('MyPatchedClass');
     *                super.print();
     *            }
     *        }
     *    );
     *
     *    const myPatchedClass = new MyPatchedClass();
     *    myPatchedClass.print(); // displays "MyPatchedClass" and "MyClass"
     *
     *
     * The 'unpatch' function can be used to remove a patch, given its key:
     *
     *    MyPatchedClass.unpatch("module_name.key");
     */
    function patchMixin(OriginalClass) {
        let unpatchList = [];
        class PatchableClass extends OriginalClass {}

        PatchableClass.patch = function (name, patch) {
            if (unpatchList.find(x => x.name === name)) {
                throw new Error(`Class ${OriginalClass.name} already has a patch ${name}`);
            }
            if (!Object.prototype.hasOwnProperty.call(this, 'patch')) {
                throw new Error(`Class ${this.name} is not patchable`);
            }
            const SubClass = patch(Object.getPrototypeOf(this));
            unpatchList.push({
                name: name,
                elem: this,
                prototype: this.prototype,
                origProto: Object.getPrototypeOf(this),
                origPrototype: Object.getPrototypeOf(this.prototype),
                patch: patch,
            });
            Object.setPrototypeOf(this, SubClass);
            Object.setPrototypeOf(this.prototype, SubClass.prototype);
        };

        PatchableClass.unpatch = function (name) {
            if (!unpatchList.find(x => x.name === name)) {
                throw new Error(`Class ${OriginalClass.name} does not have any patch ${name}`);
            }
            const toUnpatch = unpatchList.reverse();
            unpatchList = [];
            for (let unpatch of toUnpatch) {
                Object.setPrototypeOf(unpatch.elem, unpatch.origProto);
                Object.setPrototypeOf(unpatch.prototype, unpatch.origPrototype);
            }
            for (let u of toUnpatch.reverse()) {
                if (u.name !== name) {
                    PatchableClass.patch(u.name, u.patch);
                }
            }
        };
        return PatchableClass;
    }

    return patchMixin;
});
