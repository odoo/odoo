// @ts-check

/** @module @web/legacy/js/core/class - Legacy class inheritance system based on John Resig's simple JavaScript inheritance */

/**
 * Improved John Resig's inheritance, based on:
 *
 * Simple JavaScript Inheritance
 * By John Resig http://ejohn.org/
 * MIT Licensed.
 *
 * Adds "include()"
 *
 * Defines The Class object. That object can be used to define and inherit classes using
 * the extend() method.
 *
 * Example::
 *
 *     var Person = Class.extend({
 *      init: function(isDancing){
 *         this.dancing = isDancing;
 *       },
 *       dance: function(){
 *         return this.dancing;
 *       }
 *     });
 *
 * The init() method act as a constructor. This class can be instanced this way::
 *
 *     var person = new Person(true);
 *     person.dance();
 *
 *     The Person class can also be extended again:
 *
 *     var Ninja = Person.extend({
 *       init: function(){
 *         this._super( false );
 *       },
 *       dance: function(){
 *         // Call the inherited version of dance()
 *         return this._super();
 *       },
 *       swingSword: function(){
 *         return true;
 *       }
 *     });
 *
 * When extending a class, each re-defined method can use this._super() to call the previous
 * implementation of that method.
 *
 * @class Class
 */
function OdooClass() {}

let initializing = false;

const fnTest = /xyz/.test(
    function () {
        // @ts-expect-error -- function body is only stringified via toString(); xyz is never executed
        xyz();
    }.toString(),
)
    ? /\b_super\b/
    : /.*/;

/**
 * Subclass an existing class. Accepts one or more mixin objects as arguments.
 *
 * @param {...Record<string, any>} mixins class-level properties and instance methods
 * @returns {Function} the new subclass constructor
 */
OdooClass.extend = function () {
    const _super = this.prototype;
    // Support mixins arguments
    const args = [...arguments];
    args.unshift({});

    const prop = {};
    args.forEach((arg) => {
        Object.assign(prop, arg);
    });

    // Instantiate a web class (but only create the instance,
    // don't run the init constructor)
    initializing = true;
    const This = this;
    const prototype = new This();
    initializing = false;

    // Copy the properties over onto the new prototype
    for (const name of Object.keys(prop)) {
        // Check if we're overwriting an existing function
        prototype[name] =
            typeof prop[name] == "function" && fnTest.test(prop[name])
                ? (function (name, fn) {
                      return function () {
                          const tmp = this._super;

                          // Add a new ._super() method that is the same
                          // method but on the super-class
                          this._super = _super[name];

                          // The method only need to be bound temporarily, so
                          // we remove it when we're done executing
                          const ret = fn.apply(this, arguments);
                          this._super = tmp;

                          return ret;
                      };
                  })(name, prop[name])
                : prop[name];
    }

    // The dummy class constructor
    function Class() {
        if (this.constructor !== OdooClass) {
            throw new Error(
                "You can only instanciate objects with the 'new' operator",
            );
        }
        // All construction is actually done in the init method
        this._super = null;
        // Cast to any: init() is injected dynamically by the mixin system
        const self = /** @type {any} */ (this);
        if (!initializing && self.init) {
            const ret = self.init.apply(self, arguments);
            if (ret) {
                return ret;
            }
        }
        return this;
    }
    /**
     * Adds or overrides methods on an existing class without creating a subclass.
     *
     * @param {Record<string, any>} properties
     * @returns {void}
     */
    Class.include = function (properties) {
        for (const name of Object.keys(properties)) {
            if (
                typeof properties[name] !== "function" ||
                !fnTest.test(properties[name])
            ) {
                prototype[name] = properties[name];
            } else if (
                typeof prototype[name] === "function" &&
                Object.hasOwn(prototype, name)
            ) {
                prototype[name] = (function (name, fn, previous) {
                    return function () {
                        const tmp = this._super;
                        this._super = previous;
                        const ret = fn.apply(this, arguments);
                        this._super = tmp;
                        return ret;
                    };
                })(name, properties[name], prototype[name]);
            } else if (typeof _super[name] === "function") {
                prototype[name] = (function (name, fn) {
                    return function () {
                        const tmp = this._super;
                        this._super = _super[name];
                        const ret = fn.apply(this, arguments);
                        this._super = tmp;
                        return ret;
                    };
                })(name, properties[name]);
            }
        }
    };

    // Populate our constructed prototype object
    Class.prototype = prototype;

    // Enforce the constructor to be what we expect
    Class.constructor = Class;

    // And make this class extendable
    Class.extend = this.extend;

    return Class;
};

export default OdooClass;
