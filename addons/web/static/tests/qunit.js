/** @odoo-module */

import { isVisible as isElemVisible } from "@web/core/utils/ui";
import { fullTraceback, fullAnnotatedTraceback } from "@web/core/errors/error_utils";
import { registry } from "@web/core/registry";
import { Component, whenReady } from "@odoo/owl";

const consoleError = console.error;

function setQUnitDebugMode() {
    whenReady(() => document.body.classList.add("debug")); // make the test visible to the naked eye
    QUnit.config.debug = true; // allows for helper functions to behave differently (logging, the HTML element in which the test occurs etc...)
    QUnit.config.testTimeout = 60 * 60 * 1000;
    // Allows for interacting with the test when it is over
    // In fact, this will pause QUnit.
    // Also, logs useful info in the console.
    QUnit.testDone(async (...args) => {
        console.groupCollapsed("Debug Test output");
        console.log(...args);
        console.groupEnd();
        await new Promise(() => {});
    });
}

// need to do this outside of the setup function so the QUnit.debug is defined when we need it
QUnit.debug = (name, cb) => {
    setQUnitDebugMode();
    QUnit.only(name, cb);
};

// need to do this outside of the setup function so it is executed quickly
QUnit.config.autostart = false;

export function setupQUnit() {
    // -----------------------------------------------------------------------------
    // QUnit config
    // -----------------------------------------------------------------------------
    QUnit.config.testTimeout = 1 * 60 * 1000;
    QUnit.config.hidepassed = window.location.href.match(/[?&]testId=/) === null;

    // -----------------------------------------------------------------------------
    // QUnit assert
    // -----------------------------------------------------------------------------
    /**
     * Checks that the target contains exactly n matches for the selector.
     *
     * Example: assert.containsN(document.body, '.modal', 0)
     */
    function containsN(target, selector, n, msg) {
        let $el;
        if (target._widgetRenderAndInsert) {
            $el = target.$el; // legacy widget
        } else if (target instanceof Component) {
            if (!target.el) {
                throw new Error(
                    `containsN assert with selector '${selector}' called on an unmounted component`
                );
            }
            $el = $(target.el);
        } else {
            $el = target instanceof Element ? $(target) : target;
        }
        msg = msg || `Selector '${selector}' should have exactly ${n} matches inside the target`;
        QUnit.assert.strictEqual($el.find(selector).length, n, msg);
    }

    /**
     * Checks that the target contains exactly 0 match for the selector.
     *
     * @param {Element} el
     * @param {string} selector
     * @param {string} [msg]
     */
    function containsNone(target, selector, msg) {
        containsN(target, selector, 0, msg);
    }

    /**
     * Checks that the target contains exactly 1 match for the selector.
     *
     * @param {Element} el
     * @param {string} selector
     * @param {string} [msg]
     */
    function containsOnce(target, selector, msg) {
        containsN(target, selector, 1, msg);
    }

    /**
     * Helper function, to check if a given element has (or has not) classnames.
     *
     * @private
     * @param {Element | jQuery | Widget} el
     * @param {string} classNames
     * @param {boolean} shouldHaveClass
     * @param {string} [msg]
     */
    function _checkClass(el, classNames, shouldHaveClass, msg) {
        if (el) {
            if (el._widgetRenderAndInsert) {
                el = el.el; // legacy widget
            } else if (!(el instanceof Element)) {
                el = el[0];
            }
        }
        msg =
            msg ||
            `target should ${shouldHaveClass ? "have" : "not have"} classnames ${classNames}`;
        const isFalse = classNames.split(" ").some((cls) => {
            const hasClass = el.classList.contains(cls);
            return shouldHaveClass ? !hasClass : hasClass;
        });
        QUnit.assert.ok(!isFalse, msg);
    }

    /**
     * Checks that the target element has the given classnames.
     *
     * @param {Element} el
     * @param {string} classNames
     * @param {string} [msg]
     */
    function hasClass(el, classNames, msg) {
        _checkClass(el, classNames, true, msg);
    }

    /**
     * Checks that the target element does not have the given classnames.
     *
     * @param {Element} el
     * @param {string} classNames
     * @param {string} [msg]
     */
    function doesNotHaveClass(el, classNames, msg) {
        _checkClass(el, classNames, false, msg);
    }

    /**
     * Checks that the target element (described by widget/jquery or html element)
     * - exists
     * - is unique
     * - has the given attribute with the proper value
     *
     * @param {Component | Element | Widget | jQuery} w
     * @param {string} attr
     * @param {string} value
     * @param {string} [msg]
     */
    function hasAttrValue(target, attr, value, msg) {
        let $el;
        if (target._widgetRenderAndInsert) {
            $el = target.$el; // legacy widget
        } else if (target instanceof Component) {
            if (!target.el) {
                throw new Error(
                    `hasAttrValue assert with attr '${attr}' called on an unmounted component`
                );
            }
            $el = $(target.el);
        } else {
            $el = target instanceof Element ? $(target) : target;
        }

        if ($el.length !== 1) {
            const descr = `hasAttrValue (${attr}: ${value})`;
            QUnit.assert.ok(
                false,
                `Assertion '${descr}' targets ${$el.length} elements instead of 1`
            );
        } else {
            msg = msg || `attribute '${attr}' of target should be '${value}'`;
            QUnit.assert.strictEqual($el.attr(attr), value, msg);
        }
    }

    /**
     * Helper function, to check if a given element
     * - is unique (if it is a jquery node set)
     * - is (or not) visible
     *
     * @private
     * @param {Element | jQuery | Widget} el
     * @param {boolean} shouldBeVisible
     * @param {string} [msg]
     */
    function _checkVisible(el, shouldBeVisible, msg) {
        if (el) {
            if (el._widgetRenderAndInsert) {
                el = el.el; // legacy widget
            } else if (!(el instanceof Element)) {
                el = el[0];
            }
        }
        msg = msg || `target should ${shouldBeVisible ? "" : "not"} be visible`;
        const _isVisible = isElemVisible(el);
        const condition = shouldBeVisible ? _isVisible : !_isVisible;
        QUnit.assert.ok(condition, msg);
    }
    function isVisible(el, msg) {
        return _checkVisible(el, true, msg);
    }
    function isNotVisible(el, msg) {
        return _checkVisible(el, false, msg);
    }
    function expectErrors() {
        QUnit.config.current.expectErrors = true;
        QUnit.config.current.unverifiedErrors = [];
    }
    function verifyErrors(expectedErrors) {
        if (!QUnit.config.current.expectErrors) {
            QUnit.pushFailure(`assert.expectErrors() must be called at the beginning of the test`);
            return;
        }
        const unverifiedErrors = QUnit.config.current.unverifiedErrors;
        QUnit.config.current.assert.deepEqual(unverifiedErrors, expectedErrors, "verifying errors");
        QUnit.config.current.unverifiedErrors = [];
    }
    QUnit.assert.containsN = containsN;
    QUnit.assert.containsNone = containsNone;
    QUnit.assert.containsOnce = containsOnce;
    QUnit.assert.doesNotHaveClass = doesNotHaveClass;
    QUnit.assert.hasClass = hasClass;
    QUnit.assert.hasAttrValue = hasAttrValue;
    QUnit.assert.isVisible = isVisible;
    QUnit.assert.isNotVisible = isNotVisible;
    QUnit.assert.expectErrors = expectErrors;
    QUnit.assert.verifyErrors = verifyErrors;

    // -----------------------------------------------------------------------------
    // QUnit logs
    // -----------------------------------------------------------------------------

    /**
     * If we want to log several errors, we have to log all of them at once, as
     * browser_js is closed as soon as an error is logged.
     */
    let errorMessages = [];
    async function logErrors() {
        const messages = errorMessages.slice();
        errorMessages = [];
        const infos = await Promise.all(messages);
        consoleError(infos.map((info) => info.error || info).join("\n"));
        // Only log the source of the errors in "info" log level to allow matching the same
        // error with its log message, as source contains asset file name which changes
        console.info(
            infos
                .map((info) =>
                    info.source ? `${info.error}\n${info.source.replace(/^/gm, "\t")}\n` : info
                )
                .join("\n")
        );
    }

    /**
     * If we want to log several errors, we have to log all of them at once, as
     * browser_js is closed as soon as an error is logged.
     */
    QUnit.done(async (result) => {
        await odoo.loader.checkErrorProm;
        const moduleLoadingError = document.querySelector(".o_module_error");
        if (moduleLoadingError) {
            errorMessages.unshift(moduleLoadingError.innerText);
        }
        if (result.failed) {
            errorMessages.push(`${result.failed} / ${result.total} tests failed.`);
        }
        if (!result.failed && !moduleLoadingError) {
            console.log("QUnit test suite done.");
            console.log("test successful"); // for ChromeBowser to know it's over and ok
        } else {
            logErrors();
        }
    });

    /**
     * This is done mostly for the .txt log file generated by the runbot.
     */
    QUnit.moduleDone(async (result) => {
        if (!result.failed) {
            console.log('"' + result.name + '"', "passed", result.total, "tests.");
        } else {
            console.log(
                '"' + result.name + '"',
                "failed",
                result.failed,
                "tests out of",
                result.total,
                "."
            );
        }
    });

    /**
     * This logs various data in the console, which will be available in the log
     * .txt file generated by the runbot.
     */
    QUnit.log((result) => {
        if (result.result) {
            return;
        }
        errorMessages.push(
            Promise.resolve(result.annotateProm).then(() => {
                let info = `QUnit test failed: ${result.module} > ${result.name} :`;
                if (result.message) {
                    info += `\n\tmessage: "${result.message}"`;
                }
                if ("expected" in result) {
                    info += `\n\texpected: "${result.expected}"`;
                }
                if (result.actual !== null) {
                    info += `\n\tactual: "${result.actual}"`;
                }
                return {
                    error: info,
                    source: result.source,
                };
            })
        );
    });

    /**
     * The purpose of this function is to reset the timer nesting level of the execution context
     * to 0, to prevent situations where a setTimeout with a timeout of 0 may end up being
     * scheduled after another one that also has a timeout of 0 that was called later.
     * Example code:
     * (async () => {
     *     const timeout = () => new Promise((resolve) => setTimeout(resolve, 0));
     *     const animationFrame = () => new Promise((resolve) => requestAnimationFrame(resolve));
     *
     *     for (let i = 0; i < 4; i++) {
     *         await timeout();
     *     }
     *     timeout().then(() => console.log("after timeout"));
     *     await animationFrame()
     *     timeout().then(() => console.log("after animationFrame"));
     *     // logs "after animationFrame" before "after timeout"
     * })()
     *
     * When the browser runs a task that was the result of a timer (setTimeout or setInterval),
     * that task has an intrinsic "timer nesting level". If you schedule another task with
     * a timer from within such a task, the new task has the existing task's timer nesting level,
     * plus one. When the timer nesting level of a task is greater than 5, the `timeout` parameter
     * for setTimeout/setInterval will be forced to at least 4 (see step 5 in the timer initialization
     * steps in the HTML spec: https://html.spec.whatwg.org/multipage/timers-and-user-prompts.html#timer-initialisation-steps).
     *
     * In the above example, every `await timeout()` besides inside the loop schedules a new task
     * from within a task that was initiated by a timer, causing the nesting level to be 5 after
     * the loop. The first timeout after the loop is now forced to 4.
     *
     * When we await the animation frame promise, we create a task that is *not* initiated by a timer,
     * reseting the nesting level to 0, causing the timeout following it to properly be treated as 0,
     * as such the callback that was registered by it is oftentimes executed before the previous one.
     *
     * While we can't prevent this from happening within a given test, we want to at least prevent
     * the timer nesting level to propagate from one test to the next as this can be a cause of
     * indeterminism. To avoid slowing down the tests by waiting one frame after every test,
     * we instead use a MessageChannel to add a task with not nesting level to the event queue immediately.
     */
    QUnit.testDone(async () => {
        return new Promise((resolve) => {
            const channel = new MessageChannel();
            channel.port1.onmessage = () => {
                channel.port1.close();
                channel.port2.close();
                resolve();
            };
            channel.port2.postMessage("");
        });
    });

    // Append a "Rerun in debug" link.
    // Only works if the test is not hidden.
    QUnit.testDone(async ({ testId }) => {
        if (errorMessages.length > 0) {
            logErrors();
        }
        const testElement = document.getElementById(`qunit-test-output-${testId}`);
        if (!testElement) {
            // Is probably hidden because it passed
            return;
        }
        const reRun = testElement.querySelector("li a");
        const reRunDebug = document.createElement("a");
        reRunDebug.textContent = "Rerun in debug";
        const url = new URL(window.location);
        url.searchParams.set("testId", testId);
        url.searchParams.set("debugTest", "true");
        reRunDebug.setAttribute("href", url.href);
        reRun.parentElement.insertBefore(reRunDebug, reRun.nextSibling);
    });

    const debugTest = new URLSearchParams(location.search).get("debugTest");
    if (debugTest) {
        setQUnitDebugMode();
    }

    // Override global UnhandledRejection that is assigned wayyy before this file
    // Do not really crash on non-errors rejections
    const qunitUnhandledReject = QUnit.onUnhandledRejection;
    QUnit.onUnhandledRejection = (reason) => {
        const error = reason instanceof Error && "cause" in reason ? reason.cause : reason;
        if (error instanceof Error) {
            qunitUnhandledReject(reason);
        }
    };

    // Essentially prevents default error logging when the rejection was
    // not due to an actual error
    const windowUnhandledReject = window.onunhandledrejection;
    window.onunhandledrejection = (ev) => {
        const error =
            ev.reason instanceof Error && "cause" in ev.reason ? ev.reason.cause : ev.reason;
        if (!(error instanceof Error)) {
            ev.stopImmediatePropagation();
            ev.preventDefault();
        } else if (windowUnhandledReject) {
            windowUnhandledReject.call(window, ev);
        }
    };

    // -----------------------------------------------------------------------------
    // FailFast
    // -----------------------------------------------------------------------------
    /**
     * We add here a 'fail fast' feature: we often want to stop the test suite after
     * the first failed test.  This is also useful for the runbot test suites.
     */
    QUnit.config.urlConfig.push({
        id: "failfast",
        label: "Fail Fast",
        tooltip: "Stop the test suite immediately after the first failed test.",
    });

    QUnit.begin(function () {
        if (odoo.debug && odoo.debug.includes("assets")) {
            QUnit.annotateTraceback = fullAnnotatedTraceback;
        } else {
            QUnit.annotateTraceback = (err) => Promise.resolve(fullTraceback(err));
        }
        const config = QUnit.config;
        if (config.failfast) {
            QUnit.testDone(function (details) {
                if (details.failed > 0) {
                    config.queue.length = 0;
                }
            });
        }
    });

    // -----------------------------------------------------------------------------
    // Add sort button
    // -----------------------------------------------------------------------------

    let sortButtonAppended = false;
    /**
     * Add a sort button on top of the QUnit result page, so we can see which tests
     * take the most time.
     */
    function addSortButton() {
        sortButtonAppended = true;
        var $sort = $("<label> sort by time (desc)</label>").css({ float: "right" });
        $("h2#qunit-userAgent").append($sort);
        $sort.click(function () {
            var $ol = $("ol#qunit-tests");
            var $results = $ol.children("li").get();
            $results.sort(function (a, b) {
                var timeA = Number($(a).find("span.runtime").first().text().split(" ")[0]);
                var timeB = Number($(b).find("span.runtime").first().text().split(" ")[0]);
                if (timeA < timeB) {
                    return 1;
                } else if (timeA > timeB) {
                    return -1;
                } else {
                    return 0;
                }
            });
            $.each($results, function (idx, $itm) {
                $ol.append($itm);
            });
        });
    }

    QUnit.done(() => {
        if (!sortButtonAppended) {
            addSortButton();
        }
    });

    // -----------------------------------------------------------------------------
    // Add statistics
    // -----------------------------------------------------------------------------

    let passedEl;
    let failedEl;
    let skippedEl;
    let todoCompletedEl;
    let todoUncompletedEl;
    function insertStats() {
        const toolbar = document.querySelector("#qunit-testrunner-toolbar .qunit-url-config");
        const statsEl = document.createElement("label");
        passedEl = document.createElement("span");
        passedEl.classList.add("text-success", "ms-5", "me-3");
        statsEl.appendChild(passedEl);
        todoCompletedEl = document.createElement("span");
        todoCompletedEl.classList.add("text-warning", "me-3");
        statsEl.appendChild(todoCompletedEl);
        failedEl = document.createElement("span");
        failedEl.classList.add("text-danger", "me-3");
        statsEl.appendChild(failedEl);
        todoUncompletedEl = document.createElement("span");
        todoUncompletedEl.classList.add("text-primary", "me-3");
        statsEl.appendChild(todoUncompletedEl);
        skippedEl = document.createElement("span");
        skippedEl.classList.add("text-dark");
        statsEl.appendChild(skippedEl);
        toolbar.appendChild(statsEl);
    }

    let testPassedCount = 0;
    let testFailedCount = 0;
    let testSkippedCount = 0;
    let todoCompletedCount = 0;
    let todoUncompletedCount = 0;
    QUnit.testDone(({ skipped, failed, todo }) => {
        if (!passedEl) {
            insertStats();
        }
        if (!skipped) {
            if (failed > 0) {
                if (todo) {
                    todoUncompletedCount++;
                } else {
                    testFailedCount++;
                }
            } else {
                if (todo) {
                    todoCompletedCount++;
                } else {
                    testPassedCount++;
                }
            }
        } else {
            testSkippedCount++;
        }
        passedEl.innerText = `${testPassedCount} passed`;
        if (todoCompletedCount > 0) {
            todoCompletedEl.innerText = `${todoCompletedCount} todo completed`;
        }
        if (todoUncompletedCount > 0) {
            todoUncompletedEl.innerText = `${todoUncompletedCount} todo uncompleted`;
        }
        if (testFailedCount > 0) {
            failedEl.innerText = `${testFailedCount} failed`;
        }
        if (testSkippedCount > 0) {
            skippedEl.innerText = `${testSkippedCount} skipped`;
        }
    });

    // -----------------------------------------------------------------------------
    // FIXME: This sounds stupid, it feels stupid... but it fixes visibility check in folded <details> since Chromium 97+ 💩
    // Since https://bugs.chromium.org/p/chromium/issues/detail?id=1185950
    // See regression report https://bugs.chromium.org/p/chromium/issues/detail?id=1276028
    // -----------------------------------------------------------------------------

    QUnit.begin(() => {
        const el = document.createElement("style");
        el.innerText = "details:not([open]) > :not(summary) { display: none; }";
        document.head.appendChild(el);
    });

    // -----------------------------------------------------------------------------
    // Error management
    // -----------------------------------------------------------------------------

    QUnit.on("OdooAfterTestHook", (info) => {
        const { expectErrors, unverifiedErrors } = QUnit.config.current;
        if (expectErrors && unverifiedErrors.length) {
            QUnit.pushFailure(
                `Expected assert.verifyErrors() to be called before end of test. Unverified errors: ${unverifiedErrors}`
            );
        }
    });

    const { onUnhandledRejection } = QUnit;
    QUnit.onUnhandledRejection = () => {};
    QUnit.onError = () => {};

    console.error = function () {
        if (QUnit.config.current) {
            QUnit.pushFailure(`console.error called with "${arguments[0]}"`);
        } else {
            consoleError(...arguments);
        }
    };

    function onUncaughtErrorInTest(error) {
        if (!QUnit.config.current.expectErrors) {
            // we did not expect any error, so notify qunit to add a failure
            onUnhandledRejection(error);
        } else {
            // we expected errors, so store it, it will be checked later (see verifyErrors)
            while (error instanceof Error && "cause" in error) {
                error = error.cause;
            }
            QUnit.config.current.unverifiedErrors.push(error.message);
        }
    }

    // e.g. setTimeout(() => throw new Error()) (event handler crashes synchronously)
    window.addEventListener("error", async (ev) => {
        if (!QUnit.config.current) {
            return; // we are not in a test -> do nothing
        }
        // do not log to the console as this will kill python test early
        ev.preventDefault();
        // if the error service is deployed, we'll get to the patched default handler below if no
        // other handler handled the error, so do nothing here
        if (registry.category("services").get("error", false)) {
            return;
        }
        if (
            ev.message === "ResizeObserver loop limit exceeded" ||
            ev.message === "ResizeObserver loop completed with undelivered notifications."
        ) {
            return;
        }
        onUncaughtErrorInTest(ev.error);
    });

    // e.g. Promise.resolve().then(() => throw new Error()) (crash in event handler after async boundary)
    window.addEventListener("unhandledrejection", async (ev) => {
        if (!QUnit.config.current) {
            return; // we are not in a test -> do nothing
        }
        // do not log to the console as this will kill python test early
        ev.preventDefault();
        // if the error service is deployed, we'll get to the patched default handler below if no
        // other handler handled the error, so do nothing here
        if (registry.category("services").get("error", false)) {
            return;
        }
        onUncaughtErrorInTest(ev.reason);
    });

    // This is an approximation, but we can't directly import the default error handler, because
    // it's not the same in all tested environments (e.g. /web and /pos), so we get the last item
    // from the handler registry and assume it is the default one, which handles all "not already
    // handled" errors, like tracebacks.
    const errorHandlerRegistry = registry.category("error_handlers");
    const [defaultHandlerName, defaultHandler] = errorHandlerRegistry.getEntries().at(-1);
    const testDefaultHandler = (env, uncaughtError, originalError) => {
        onUncaughtErrorInTest(originalError);
        return defaultHandler(env, uncaughtError, originalError);
    };
    errorHandlerRegistry.add(defaultHandlerName, testDefaultHandler, {
        sequence: Number.POSITIVE_INFINITY,
        force: true,
    });
}
