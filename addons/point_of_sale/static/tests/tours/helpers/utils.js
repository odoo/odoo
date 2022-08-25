odoo.define('point_of_sale.tour.utils', function (require) {
    'use strict';

    const config = require('web.config');

    /**
     * USAGE
     * -----
     *
     * ```
     * const { startSteps, getSteps, createTourMethods } = require('point_of_sale.utils');
     * const { Other } = require('point_of_sale.tour.OtherMethods');
     *
     * // 1. Define classes Do, Check and Execute having methods that
     * //    each return array of tour steps.
     * class Do {
     *   click() {
     *      return [{ content: 'click button', trigger: '.button' }];
     *   }
     * }
     * class Check {
     *   isHighligted() {
     *      return [{ content: 'button is highlighted', trigger: '.button.highlight', run: () => {} }];
     *   }
     * }
     * // Notice that Execute has access to methods defined in Do and Check classes
     * // Also, we can compose steps from other module.
     * class Execute {
     *   complexSteps() {
     *      return [...this._do.click(), ...this._check.isHighlighted(), ...Other._exec.complicatedSteps()];
     *   }
     * }
     *
     * // 2. Instantiate these class definitions using `createTourMethods`.
     * //    The returned object gives access to the defined methods above
     * //    thru the do, check and exec properties.
     * //    - do gives access to the methods defined in Do class
     * //    - check gives access to the methods defined in Check class
     * //    - exec gives access to the methods defined in Execute class
     * const Screen = createTourMethods('Screen', Do, Check, Execute);
     *
     * // 3. Call `startSteps` to start empty steps.
     * startSteps();
     *
     * // 4. Call the tour methods to populate the steps created by `startSteps`.
     * Screen.do.click();               // return of this method call is added to steps created by startSteps
     * Screen.check.isHighlighted()     // same as above
     * Screen.exec.complexSteps()     // same as above
     *
     * // 5. Call `getSteps` which returns the generated tour steps.
     * const steps = getSteps();
     * ```
     */
    let steps = [];

    function startSteps() {
        // always start by waiting for loading to finish
        steps = [
            {
                content: 'wait for loading to finish',
                trigger: 'body:not(:has(.loader))',
                run: function () {},
            },
        ];
    }

    function getSteps() {
        return steps;
    }

    // this is the method decorator
    // when the method is called, the generated steps are added
    // to steps
    const methodProxyHandler = {
        apply(target, thisArg, args) {
            const res = target.call(thisArg, ...args);
            if (config.isDebug()) {
                // This step is added before the real steps.
                // Very useful when debugging because we know which
                // method call failed and what were the parameters.
                const constructor = thisArg.constructor.name.split(' ')[1];
                const methodName = target.name.split(' ')[1];
                const argList = args
                    .map((a) => (typeof a === 'string' ? `'${a}'` : `${a}`))
                    .join(', ');
                steps.push({
                    content: `DOING "${constructor}.${methodName}(${argList})"`,
                    trigger: '.pos',
                    run: () => {},
                });
            }
            steps.push(...res);
            return res;
        },
    };

    // we proxy get of the method to decorate the method call
    const proxyHandler = {
        get(target, key) {
            const method = target[key];
            if (!method) {
                throw new Error(`Tour method '${key}' is not available.`);
            }
            return new Proxy(method.bind(target), methodProxyHandler);
        },
    };

    /**
     * Creates an object with `do`, `check` and `exec` properties which are instances of
     * the given `Do`, `Check` and `Execute` classes, respectively. Calling methods
     * automatically adds the returned steps to the steps created by `startSteps`.
     *
     * There are however underscored version (_do, _check, _exec).
     * Calling methods thru the underscored version does not automatically
     * add the returned steps to the current steps array. Useful when composing
     * steps from other methods.
     *
     * @param {String} name
     * @param {Function} Do class containing methods which return array of tour steps
     * @param {Function} Check similar to Do class but the steps are mainly for checking
     * @param {Function} Execute class containing methods which return array of tour steps
     *                   but has access to methods of Do and Check classes via .do and .check,
     *                   respectively. Here, we define methods that return tour steps based
     *                   on the combination of steps from Do and Check.
     */
    function createTourMethods(name, Do, Check = class {}, Execute = class {}) {
        Object.defineProperty(Do, 'name', { value: `${name}.do` });
        Object.defineProperty(Check, 'name', { value: `${name}.check` });
        Object.defineProperty(Execute, 'name', {
            value: `${name}.exec`,
        });
        const methods = { do: new Do(), check: new Check(), exec: new Execute() };
        // Allow Execute to have access to methods defined in Do and Check
        // via do and exec, respectively.
        methods.exec._do = methods.do;
        methods.exec._check = methods.check;
        return {
            Do,
            Check,
            Execute,
            [name]: {
                do: new Proxy(methods.do, proxyHandler),
                check: new Proxy(methods.check, proxyHandler),
                exec: new Proxy(methods.exec, proxyHandler),
                _do: methods.do,
                _check: methods.check,
                _exec: methods.exec,
            },
        };
    }

    return { startSteps, getSteps, createTourMethods };
});
