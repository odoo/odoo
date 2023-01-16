// Type definitions for QUnit v2.9.2
// Project: http://qunitjs.com/
// Definitions by: James Bracy <https://github.com/waratuman>
//                 Mike North <https://github.com/mike-north>
//                 Stefan Sechelmann <https://github.com/sechel>
//                 Chris Krycho <https://github.com/chriskrycho>
//                 Dan Freeman <https://github.com/dfreeman>
//                 James C. Davis <https://github.com/jamescdavis>
// Definitions: https://github.com/DefinitelyTyped/DefinitelyTyped

// Updated for odoo.

interface Assert {
    // -----------------------------------------------------------------------------
    // Start of Odoo added asserts
    // -----------------------------------------------------------------------------
    /**
     * Checks that the target contains exactly n matches for the selector.
     *
     * Example: assert.containsN(document.body, '.modal', 0)
     */
    containsN(target: HTMLElement, selector: String, n: Number, msg?: string): void;
  
    /**
     * Checks that the target contains exactly 0 match for the selector.
     */
    containsNone(target: HTMLElement, selector: String, msg?: string): void;
  
    /**
     * Checks that the target contains exactly 1 match for the selector.
     */
    containsOnce(target: HTMLElement, selector: String, msg?: string): void;
  
    /**
     * Helper function, to check if a given element has (or has not) classnames.
     *
     * @private
     * @param {HTMLElement|jQuery|Widget} el
     */
    _checkClass(el: HTMLElement, classNames: String, shouldHaveClass: boolean, msg?: string): void;
  
    /**
     * Checks that the target element has the given classnames.
     */
    hasClass(el: HTMLElement, classNames: String, msg?: string): void;
  
    /**
     * Checks that the target element does not have the given classnames.
     */
    doesNotHaveClass(el: HTMLElement, classNames: String, msg?: string): void;
  
    /**
     * Checks that the target element (described by widget/jquery or html element)
     * - exists
     * - is unique
     * - has the given attribute with the proper value
     *
     * @param {Widget|jQuery|HTMLElement|owl.Component} target
     */
    hasAttrValue(target: HTMLElement, attr: string, value: string, msg?: string): void;
  
    /**
     * Helper function, to check if a given element
     * - is unique (if it is a jquery node set)
     * - is (or not) visible
     *
     * @private
     * @param {HTMLElement|jQuery|Widget} el
     */
    _checkVisible(el: HTMLElement, shouldBeVisible: boolean, msg?: string): void;
    
    /**
     * Check if element is visible
     * 
     * @param {HTMLElement|jQuery|Widget} el
     */
    isVisible(el: HTMLElement, msg?: string): void;
    
    /**
     * Check if element is visible
     * 
     * @param {HTMLElement|jQuery|Widget} el
     */
    isNotVisible(el:HTMLElement , msg?: string): void;

    // -----------------------------------------------------------------------------
    // End of Odoo added asserts
    // -----------------------------------------------------------------------------
  
    /**
     * Instruct QUnit to wait for an asynchronous operation.
     *
     * The callback returned from `assert.async()` will throw an Error if it is
     * invoked more than once (or more often than the accepted call count, if
     * provided).
     *
     * This replaces functionality previously provided by `QUnit.stop()` and
     * `QUnit.start()`.
     *
     * @param {number} [acceptCallCount=1] Number of expected callbacks before the test is done.
     */
    async(acceptCallCount?: number): () => void;
  
    /**
     * A deep recursive comparison, working on primitive types, arrays, objects,
     * regular expressions, dates and functions.
     *
     * The `deepEqual()` assertion can be used just like `equal()` when comparing
     * the value of objects, such that `{ key: value }` is equal to
     * `{ key: value }`. For non-scalar values, identity will be disregarded by
     * deepEqual.
     *
     * `notDeepEqual()` can be used to explicitly test deep, strict inequality.
     *
     * @param actual Object or Expression being tested
     * @param expected Known comparision value
     * @param {string} [message] A short description of the assertion
     */
    deepEqual<T>(actual: T, expected: T, message?: string): void;
  
    /**
     * A non-strict comparison, roughly equivalent to JUnit's assertEquals.
     *
     * The `equal` assertion uses the simple comparison operator (`==`) to
     * compare the actual and expected arguments. When they are equal, the
     * assertion passes; otherwise, it fails. When it fails, both actual and
     * expected values are displayed in the test result, in addition to a given
     * message.
     *
     *  `notEqual()` can be used to explicitly test inequality.
     *
     * `strictEqual()` can be used to test strict equality.
     *
     * @param actual Expression being tested
     * @param expected Known comparison value
     * @param {string} [message] A short description of the assertion
     */
    equal(actual: any, expected: any, message?: string): void;
  
    /**
     * Specify how many assertions are expected to run within a test.
     *
     * To ensure that an explicit number of assertions are run within any test,
     * use `assert.expect( number )` to register an expected count. If the
     * number of assertions run does not match the expected count, the test will
     * fail.
     *
     * @param {number} amount Number of assertions in this test.
     */
    expect(amount: number): void;
  
    /**
     * An inverted deep recursive comparison, working on primitive types,
     * arrays, objects, regular expressions, dates and functions.
     *
     * @param actual Object or Expression being tested
     * @param expected Known comparison value
     * @param {string} [message] A short description of the assertion
     */
    notDeepEqual(actual: any, expected: any, message?: string): void;
  
    /**
     * A non-strict comparison, checking for inequality.
     *
     * The `notEqual` assertion uses the simple inverted comparison operator
     * (`!=`) to compare the actual and expected arguments. When they aren't
     * equal, the assertion passes; otherwise, it fails. When it fails, both
     * actual and expected values are displayed in the test result, in addition
     * to a given message.
     *
     * `equal()` can be used to test equality.
     *
     * `notStrictEqual()` can be used to test strict inequality.
     *
     * @param actual Object or Expression being tested
     * @param expected Known comparison value
     * @param {string} [message] A short description of the assertion
     */
    notEqual(actual: any, expected: any, message?: string): void;
  
    /**
     * A boolean check, inverse of `ok()` and CommonJS's `assert.ok()`, and
     * equivalent to JUnit's `assertFalse()`. Passes if the first argument is
     * falsy.
     *
     * `notOk()` requires just one argument. If the argument evaluates to false,
     * the assertion passes; otherwise, it fails. If a second message argument
     * is provided, it will be displayed in place of the result.
     *
     * @param state Expression being tested
     * @param {string} [message] A short description of the assertion
     */
    notOk(state: any, message?: string): void;
  
    /**
     * A strict comparison of an object's own properties, checking for inequality.
     *
     * The `notPropEqual` assertion uses the strict inverted comparison operator
     * (`!==`) to compare the actual and expected arguments as Objects regarding
     * only their properties but not their constructors.
     *
     * When they aren't equal, the assertion passes; otherwise, it fails. When
     * it fails, both actual and expected values are displayed in the test
     * result, in addition to a given message.
     *
     * `equal()` can be used to test equality.
     *
     * `propEqual()` can be used to test strict equality of an Object properties.
     *
     * @param actual Object or Expression being tested
     * @param expected Known comparison value
     * @param {string} [message] A short description of the assertion
     */
    notPropEqual(actual: any, expected: any, message?: string): void;
  
    /**
     * A strict comparison, checking for inequality.
     *
     * The `notStrictEqual` assertion uses the strict inverted comparison
     * operator (`!==`) to compare the actual and expected arguments. When they
     * aren't equal, the assertion passes; otherwise, it fails. When it fails,
     * both actual and expected values are displayed in the test result, in
     * addition to a given message.
     *
     * `equal()` can be used to test equality.
     *
     * `strictEqual()` can be used to test strict equality.
     *
     * @param actual Object or Expression being tested
     * @param expected Known comparison value
     * @param {string} [message] A short description of the assertion
     */
    notStrictEqual(actual: any, expected: any, message?: string): void;
  
    /**
     * A boolean check, equivalent to CommonJS's assert.ok() and JUnit's
     * assertTrue(). Passes if the first argument is truthy.
     *
     * The most basic assertion in QUnit, ok() requires just one argument. If
     * the argument evaluates to true, the assertion passes; otherwise, it
     * fails. If a second message argument is provided, it will be displayed in
     * place of the result.
     *
     * @param state Expression being tested
     * @param {string} message A short description of the assertion
     */
    ok(state: any, message?: string): void;
  
    /**
     * A strict type and value comparison of an object's own properties.
     *
     * The `propEqual()` assertion provides strictly (`===`) comparison of
     * Object properties. Unlike `deepEqual()`, this assertion can be used to
     * compare two objects made with different constructors and prototype.
     *
     * `strictEqual()` can be used to test strict equality.
     *
     * `notPropEqual()` can be used to explicitly test strict inequality of
     * Object properties.
     *
     * @param actual Object or Expression being tested
     * @param expected Known comparison value
     * @param {string} [message] A short description of the assertion
     */
    propEqual(actual: any, expected: any, message?: string): void;
  
    /**
     * Report the result of a custom assertion
     *
     * Some test suites may need to express an expectation that is not defined
     * by any of QUnit's built-in assertions. This need may be met by
     * encapsulating the expectation in a JavaScript function which returns a
     * `Boolean` value representing the result; this value can then be passed
     * into QUnit's `ok` assertion.
     *
     * A more readable solution would involve defining a custom assertion. If
     * the expectation function invokes `pushResult`, QUnit will be notified of
     * the result and report it accordingly.
     *
     * @param assertionResult The assertion result
     */
    pushResult(assertResult: {
      result: boolean;
      actual: any;
      expected: any;
      message: string;
    }): void;
  
    /**
     * A strict type and value comparison.
     *
     * The `strictEqual()` assertion provides the most rigid comparison of type
     * and value with the strict equality operator (`===`).
     *
     * `equal()` can be used to test non-strict equality.
     *
     * `notStrictEqual()` can be used to explicitly test strict inequality.
     *
     * @param actual Object or Expression being tested
     * @param expected Known comparison value
     * @param {string} [message] A short description of the assertion
     */
    strictEqual<T>(actual: T, expected: T, message?: string): void;
  
    /**
     * Test if a callback throws an exception, and optionally compare the thrown
     * error.
     *
     * When testing code that is expected to throw an exception based on a
     * specific set of circumstances, use assert.throws() to catch the error
     * object for testing and comparison.
     *
     * In very few environments, like Closure Compiler, throws is considered a
     * reserved word and will cause an error. For that case, an alias is bundled
     * called `raises`. It has the same signature and behaviour, just a
     * different name.
     */
    throws(block: () => void, expected?: any, message?: any): void;
    raises(block: () => void, expected?: any, message?: any): void;
  
    /**
     * Test if the provided promise rejects, and optionally compare the
     * rejection value.
     *
     * When testing code that is expected to return a rejected promise based on
     * a specific set of circumstances, use assert.rejects() for testing and
     * comparison.
     *
     * The expectedMatcher argument can be:
     *      A function that returns true when the assertion should be considered passing.
     *      An Error object
     *      A base constructor to use ala rejectionValue instanceof expectedMatcher
     *      A RegExp that matches (or partially matches) rejectionValue.toString()
     *
     * Note: in order to avoid confusion between the message and the expectedMatcher,
     * the expectedMatcher can not be a string.
     *
     * @param promise promise to test for rejection
     * @param expectedMatcher Rejection value matcher
     * @param message A short description of the assertion
     */
    rejects(promise: Promise<any>, message?: string): Promise<void>;
    rejects(
      promise: Promise<any>,
      expectedMatcher?: any,
      message?: string
    ): Promise<void>;
  
    /**
     * A marker for progress in a given test.
     *
     * The `step()` assertion registers a passing assertion with a provided message. This makes
     * it easy to check that specific portions of code are being executed, especially in
     * asynchronous test cases and when used with `verifySteps()`.
     *
     * Together with the `verifySteps()` method, `step()` assertions give you an easy way
     * to verify both the count and order of code execution.
     *
     * @param message Message to display for the step
     */
    step(message: string): void;
  
    /**
     * A helper assertion to verify the order and number of steps in a test.
     *
     * The assert.verifySteps() assertion compares a given array of string values (representing steps)
     * with the order and values of previous step() calls. This assertion is helpful for verifying
     * the order and count of portions of code paths, especially asynchronous ones.
     *
     * @param steps Array of strings representing steps to verify
     * @param message A short description of the assertion
     */
    verifySteps(steps: string[], message?: string): void;
  }
  
  interface Config {
    altertitle: boolean;
    autostart: boolean;
    collapse: boolean;
    current: any;
    filter: string | RegExp;
    fixture: string;
    hidepassed: boolean;
    maxDepth: number;
    module: string;
    moduleId: string[];
    notrycatch: boolean;
    noglobals: boolean;
    seed: string;
    reorder: boolean;
    requireExpects: boolean;
    testId: string[];
    testTimeout: number;
    scrolltop: boolean;
    urlConfig: {
      id?: string;
      label?: string;
      tooltip?: string;
      value?: string | string[] | { [key: string]: string };
    }[];
  }
  
  interface Hooks {
    /**
     * Runs after the last test. If additional tests are defined after the
     * module's queue has emptied, it will not run this hook again.
     */
    after?: (assert: Assert) => void | Promise<void>;
  
    /**
     * Runs after each test.
     */
    afterEach?: (assert: Assert) => void | Promise<void>;
  
    /**
     * Runs before the first test.
     */
    before?: (assert: Assert) => void | Promise<void>;
  
    /**
     * Runs before each test.
     */
    beforeEach?: (assert: Assert) => void | Promise<void>;
  }
  
  interface NestedHooks {
    /**
     * Runs after the last test. If additional tests are defined after the
     * module's queue has emptied, it will not run this hook again.
     */
    after: (fn: (assert: Assert) => void | Promise<void>) => void;
  
    /**
     * Runs after each test.
     */
    afterEach: (fn: (assert: Assert) => void | Promise<void>) => void;
  
    /**
     * Runs before the first test.
     */
    before: (fn: (assert: Assert) => void | Promise<void>) => void;
  
    /**
     * Runs before each test.
     */
    beforeEach: (fn: (assert: Assert) => void | Promise<void>) => void;
  }
  
  type moduleFunc1 = (
    name: string,
    hooks?: Hooks,
    nested?: (hooks: NestedHooks) => void
  ) => void;
  type moduleFunc2 = (
    name: string,
    nested?: (hooks: NestedHooks) => void
  ) => void;
  type ModuleOnly = { only: moduleFunc1 & moduleFunc2 };
  
  declare namespace QUnitNamespace {
    interface BeginDetails {
      totalTests: number;
    }
    interface DoneDetails {
      failed: number;
      passed: number;
      total: number;
      runtime: number;
    }
    interface LogDetails {
      result: boolean;
      actual: any;
      expected: any;
      message: string;
      source: string;
      module: string;
      name: string;
      runtime: number;
    }
    interface ModuleDoneDetails {
      name: string;
      failed: number;
      passed: number;
      total: number;
      runtime: number;
    }
    interface ModuleStartDetails {
      name: string;
    }
    interface TestDoneDetails {
      name: string;
      module: string;
      failed: number;
      passed: number;
      total: number;
      runtime: number;
    }
    interface TestStartDetails {
      name: string;
      module: string;
    }
  }
  
  interface QUnit {
    /**
     * Namespace for QUnit assertions
     *
     * QUnit's built-in assertions are defined on the `QUnit.assert` object. An
     * instance of this object is passed as the only argument to the `QUnit.test`
     * function callback.
     *
     * This object has properties for each of QUnit's built-in assertion methods.
     */
    assert: Assert;
  
    /**
     * Register a callback to fire whenever the test suite begins.
     *
     * `QUnit.begin()` is called once before running any tests.
     *
     * @callback callback Callback to execute.
     */
    begin(callback: (details: QUnitNamespace.BeginDetails) => void | Promise<void>): void;
  
    /**
     * Configuration for QUnit
     *
     * QUnit has a bunch of internal configuration defaults, some of which are
     * useful to override. Check the description for each option for details.
     */
    config: Config;
  
    /**
     * Register a callback to fire whenever the test suite ends.
     *
     * @param callback Callback to execute
     */
    done(callback: (details: QUnitNamespace.DoneDetails) => void | Promise<void>): void;
  
    /**
     * Advanced and extensible data dumping for JavaScript.
     *
     * This method does string serialization by parsing data structures and
     * objects. It parses DOM elements to a string representation of their outer
     * HTML. By default, nested structures will be displayed up to five levels
     * deep. Anything beyond that is replaced by `[object Object]` and
     * `[object Array]` placeholders.
     *
     * If you need more or less output, change the value of `QUnit.dump.maxDepth`,
     * representing how deep the elements should be parsed.
     *
     * Note: This method used to be in QUnit.jsDump, which was changed to
     * QUnit.dump. The old property will be removed in QUnit 3.0.
     */
    dump: {
      maxDepth: number;
      parse(data: any): string;
    };
  
    /**
     * Copy the properties defined by the `mixin` object into the `target` object.
     *
     * This method will modify the `target` object to contain the "own" properties
     * defined by the `mixin`. If the `mixin` object specifies the value of any
     * attribute as undefined, this property will instead be removed from the
     * `target` object.
     *
     * @param target An object whose properties are to be modified
     * @param mixin An object describing which properties should be modified
     */
    extend(target: any, mixin: any): void;
  
    /**
     * Register a callback to fire whenever an assertion completes.
     *
     * This is one of several callbacks QUnit provides. Its intended for
     * integration scenarios like PhantomJS or Jenkins. The properties of the
     * details argument are listed below as options.
     *
     * @param callback Callback to execute
     */
    log(callback: (details: QUnitNamespace.LogDetails) => void): void;
  
    /**
     * Group related tests under a single label.
     *
     * You can use the module name to organize, select, and filter tests to run.
     *
     * All tests inside a module callback function will be grouped into that
     * module. The test names will all be preceded by the module name in the
     * test results. Other modules can be nested inside this callback function,
     * where their tests' names will be labeled by their names recursively
     * prefixed by their parent modules.
     *
     * If `QUnit.module` is defined without a `nested` callback argument, all
     * subsequently defined tests will be grouped into the module until another
     * module is defined.
     *
     * Modules with test group functions allow you to define nested modules, and
     * QUnit will run tests on the parent module before going deep on the nested
     * ones, even if they're declared first. Additionally, any hook callbacks on
     * a parent module will wrap the hooks on a nested module. In other words,
     * `before` and `beforeEach` callbacks will form a queue while the
     * `afterEach` and `after` callbacks will form a stack.
     *
     * You can specify code to run before and after tests using the hooks
     * argument, and also to create properties that will be shared on the
     * testing context. Any additional properties on the `hooks` object will be
     * added to that context. The `hooks` argument is still optional if you call
     * `QUnit.module` with a callback argument.
     *
     * The module's callback is invoked with the test environment as its `this`
     * context, with the environment's properties copied to the module's tests,
     * hooks, and nested modules. Note that changes on tests' `this` are not
     * preserved between sibling tests, where `this` will be reset to the initial
     * value for each test.
     *
     * @param {string} name Label for this group of tests
     * @param hookds Callbacks to run during test execution
     * @param nested A callback with grouped tests and nested modules to run under the current module label
     */
    module: moduleFunc1 & moduleFunc2 & ModuleOnly;
  
    /**
     * Register a callback to fire whenever a module ends.
     *
     * @param callback Callback to execute
     */
    moduleDone(
      callback: (details: QUnitNamespace.ModuleDoneDetails) => void | Promise<void>
    ): void;
  
    /**
     * Register a callback to fire whenever a module begins.
     *
     * @param callback Callback to execute
     */
    moduleStart(
      callback: (details: QUnitNamespace.ModuleStartDetails) => void | Promise<void>
    ): void;
  
    /**
     * Adds a test to exclusively run, preventing all other tests from running.
     *
     * Use this method to focus your test suite on a specific test. QUnit.only
     * will cause any other tests in your suite to be ignored.
     *
     * Note, that if more than one QUnit.only is present only the first instance
     * will run.
     *
     * This is an alternative to filtering tests to run in the HTML reporter. It
     * is especially useful when you use a console reporter or in a codebase
     * with a large set of long running tests.
     *
     * @param {string} name Title of unit being tested
     * @param callback Function to close over assertions
     */
    only(name: string, callback: (assert: Assert) => void | Promise<void>): void;

    /**
     * Adds a test to exclusively run in debug mode, preventing all other tests from running.
     *
     * Use this method to focus your test suite on a specific test. QUnit.debug
     * will cause any other tests in your suite to be ignored.
     *
     * Note, that if more than one QUnit.debug is present only the first instance
     * will run.
     *
     * This is an alternative to filtering tests to run in the HTML reporter. It
     * is especially useful when you use a console reporter or in a codebase
     * with a large set of long running tests.
     *
     * @param {string} name Title of unit being tested
     * @param callback Function to close over assertions
     */
    debug(name: string, callback: (assert: Assert) => void | Promise<void>): void;

    /**
     * DEPRECATED: Report the result of a custom assertion.
     *
     * This method is deprecated and it's recommended to use pushResult on its
     * direct reference in the assertion context.
     *
     * QUnit.push reflects to the current running test, and it may leak
     * assertions in asynchronous mode. Checkout assert.pushResult() to set a
     * proper custom assertion.
     *
     * Invoking QUnit.push allows to create a readable expectation that is not
     * defined by any of QUnit's built-in assertions.
     *
     * @deprecated
     */
    push(result: boolean, actual: any, expected: any, message: string): void;
  
    /**
     * Adds a test like object to be skipped.
     *
     * Use this method to replace QUnit.test() instead of commenting out entire
     * tests.
     *
     * This test's prototype will be listed on the suite as a skipped test,
     * ignoring the callback argument and the respective global and module's
     * hooks.
     *
     * @param {string} Title of unit being tested
     */
    skip(name: string, callback?: (assert: Assert) => void | Promise<void>): void;
  
    /**
     * Returns a single line string representing the stacktrace (call stack).
     *
     * This method returns a single line string representing the stacktrace from
     * where it was called. According to its offset argument, `QUnit.stack()` will
     * return the correspondent line from the call stack.
     *
     * The default `offset` is `0` and will return the current location where it
     * was called.
     *
     * Not all browsers support retrieving stracktraces. In those, `QUnit.stack()`
     * will return undefined.
     *
     * @param {number} offset Set the stacktrace line offset.
     */
    stack(offset?: number): string;
  
    /**
     * `QUnit.start()` must be used to start a test run that has
     * `QUnit.config.autostart` set to `false`.
     *
     * This method was previously used to control async tests on text contexts
     * along with QUnit.stop. For asynchronous tests, use assert.async instead.
     *
     * When your async test has multiple exit points, call `QUnit.start()` for the
     * corresponding number of `QUnit.stop()` increments.
     */
    start(): void;
  
    /**
     * Add a test to run.
     *
     * Add a test to run using `QUnit.test()`.
     *
     * The `assert` argument to the callback contains all of QUnit's assertion
     * methods. Use this argument to call your test assertions.
     *
     * `QUnit.test()` can automatically handle the asynchronous resolution of a
     * Promise on your behalf if you return a thenable Promise as the result of
     * your callback function.
     *
     * @param {string} Title of unit being tested
     * @param callback Function to close over assertions
     */
    test(name: string, callback: (assert: Assert) => void | Promise<void>): void;
  
    /**
     * Register a callback to fire whenever a test ends.
     *
     * @param callback Callback to execute
     */
    testDone(
      callback: (details: {
        name: string;
        module: string;
        failed: number;
        passed: number;
        total: number;
        runtime: number;
      }) => void | Promise<void>
    ): void;
  
    /**
     * Register a callback to fire whenever a test begins.
     *
     * @param callback Callback to execute
     */
    testStart(
      callback: (details: QUnitNamespace.TestStartDetails) => void | Promise<void>
    ): void;
  
    /**
     * Adds a test which expects at least one failing assertion during its run.
     *
     * Use this method to test a unit of code which is still under development
     * (in a “todo” state). The test will pass as long as one failing assertion
     * is present.
     *
     * If all assertions pass, then the test will fail signaling that QUnit.todo
     * should be replaced by QUnit.test.
     *
     * @param {string} Title of unit being tested
     * @param callback Function to close over assertions
     */
    todo(name: string, callback?: (assert: Assert) => void | Promise<void>): void;
  
    /**
     * Compares two values. Returns true if they are equivalent.
     *
     * @param a The first value
     * @param b The second value
     */
    equiv<T>(a: T, b: T): boolean;
  
    /**
     * Are the test running from the server or not.
     */
    isLocal: boolean;
  
    /**
     * QUnit version
     */
    version: string;
  }
  