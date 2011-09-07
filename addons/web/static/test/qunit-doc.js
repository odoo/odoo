/**
 * Defines a module scope (which lasts until the next call to module).
 *
 * This module scopes implies setup and teardown callbacks running for each test.
 *
 * @function
 * @param {String} name the name of the module
 * @param {Object} [lifecycle] callbacks to run before and after each test of the module
 * @param {Function} lifecycle.setup function running before each test of this module
 * @param {Function} lifecycle.teardown function running after each test of this module
 */
var module;
/**
 * Defines a given test to run. Runs all the assertions present in the test
 *
 * @function
 * @param {String} name the name of the test
 * @param {Number} [expected] number of assertions expected to run in this test (useful for asynchronous tests)
 * @param {Function} test the testing code to run, holding a sequence of assertions (at least one)
 */
var test;
/**
 * Defines an asynchronous test: equivalent to calling stop() at the start of
 * a normal test().
 *
 * The test code needs to restart the test runner via start()
 *
 * @function
 * @param {String} name the name of the test
 * @param {Number} [expected] number of assertions expected to run in this test (useful for asynchronous tests)
 * @param {Function} test the testing code to run, holding a sequence of assertions (at least one)
 */
var asyncTest;
/**
 * The most basic boolean assertion (~assertTrue or assert).
 *
 * Passes if its argument is truthy
 *
 * @function
 * @param {Boolean} state an arbitrary expression, evaluated in a boolean context
 * @param {String} [message] the message to output with the assertion result
 */
var ok;
/**
 * Equality assertion (~assertEqual)
 *
 * Passes if both arguments are equal (via <code>==</code>)
 *
 * @function
 * @param {Object} actual the object to check for correctness (processing result)
 * @param {Object} expected the object to check against
 * @param {String} [message] message output with the assertion result
 */
var equal;
/**
 * Inequality assertion (~assertNotEqual)
 *
 * Passes if the arguments are different (via <code>!=</code>)
 *
 * @function
 * @param {Object} actual the object to check for correctness (processing result)
 * @param {Object} expected the object to check against
 * @param {String} [message] message output with the assertion result
 */
var notEqual;
/**
 * Recursive equality assertion.
 *
 * Works on primitive types using <code>===</code> and traversing through
 * Objects and Arrays as well checking their components
 *
 * @function
 * @param {Object} actual the object to check for correctness (processing result)
 * @param {Object} expected the object to check against
 * @param {String} [message] message output with the assertion result
 */
var deepEqual;
/**
 * Recursive inequality assertion.
 *
 * Works on primitive types using <code>!==</code> and traversing through
 * Objects and Arrays as well checking their components
 *
 * @function
 * @param {Object} actual the object to check for correctness (processing result)
 * @param {Object} expected the object to check against
 * @param {String} [message] message output with the assertion result
 */
var notDeepEqual;
/**
 * Strict equality assertion (~assertEqual)
 *
 * Passes if both arguments are identical (via <code>===</code>)
 *
 * @function
 * @param {Object} actual the object to check for correctness (processing result)
 * @param {Object} expected the object to check against
 * @param {String} [message] message output with the assertion result
 */
var strictEqual;
/**
 * Strict inequality assertion (~assertNotEqual)
 *
 * Passes if both arguments are identical (via <code>!==</code>)
 *
 * @function
 * @param {Object} actual the object to check for correctness (processing result)
 * @param {Object} expected the object to check against
 * @param {String} [message] message output with the assertion result
 */
var notStrictEqual;
/**
 * Passes if the provided block raised an exception.
 *
 * The <code>expect</code> argument can be provided to perform further assertion checks on the exception itself:
 * * If it's a <code>RegExp</code> test the exception against the regexp (message?)
 * * If it's a constructor, check if the exception is an instance of it
 * * If it's an other type of function, call it with the exception as first parameter
 *   - If the function returns true, the assertion validates
 *   - Otherwise it fails
 *
 * @function
 * @param {Function} block function which should raise an exception when called
 * @param {Object} [expect] a RegExp, a constructor or a Function
 * @param {String} [message] message output with the assertion result
 */
var raises;
/**
 * Starts running the test runner again from the point where it was
 * <code>stop</code>ped.
 *
 * Used to resume testing after a callback.
 *
 * @function
 */
var start;
/**
 * Stops the test runner in order to wait for an asynchronous test to run
 *
 * @function
 * @param {Number} [timeout] fails the test after the timeout triggers, only for debugging tests
 */
var stop;
