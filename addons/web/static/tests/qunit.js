/** @odoo-module */

import { isVisible as isElemVisible } from "@web/core/utils/ui";
import { UncaughtClientError, UncaughtPromiseError } from "@web/core/errors/error_service";
import {
    completeUncaughtError,
    fullTraceback,
    fullAnnotatedTraceback,
} from "@web/core/errors/error_utils";
import { registry } from "@web/core/registry";

function setQUnitDebugMode() {
    owl.whenReady(() => document.body.classList.add("debug")); // make the test visible to the naked eye
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
    const { Component } = owl;

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
            $el = target instanceof HTMLElement ? $(target) : target;
        }
        msg = msg || `Selector '${selector}' should have exactly ${n} matches inside the target`;
        QUnit.assert.strictEqual($el.find(selector).length, n, msg);
    }

    /**
     * Checks that the target contains exactly 0 match for the selector.
     *
     * @param {HTMLElement} el
     * @param {string} selector
     * @param {string} [msg]
     */
    function containsNone(target, selector, msg) {
        containsN(target, selector, 0, msg);
    }

    /**
     * Checks that the target contains exactly 1 match for the selector.
     *
     * @param {HTMLElement} el
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
     * @param {HTMLElement|jQuery|Widget} el
     * @param {string} classNames
     * @param {boolean} shouldHaveClass
     * @param {string} [msg]
     */
    function _checkClass(el, classNames, shouldHaveClass, msg) {
        if (el) {
            if (el._widgetRenderAndInsert) {
                el = el.el; // legacy widget
            } else if (!(el instanceof HTMLElement)) {
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
     * @param {HTMLElement} el
     * @param {string} classNames
     * @param {string} [msg]
     */
    function hasClass(el, classNames, msg) {
        _checkClass(el, classNames, true, msg);
    }

    /**
     * Checks that the target element does not have the given classnames.
     *
     * @param {HTMLElement} el
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
     * @param {Widget|jQuery|HTMLElement|Component} w
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
            $el = target instanceof HTMLElement ? $(target) : target;
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
     * @param {HTMLElement|jQuery|Widget} el
     * @param {boolean} shouldBeVisible
     * @param {string} [msg]
     */
    function _checkVisible(el, shouldBeVisible, msg) {
        if (el) {
            if (el._widgetRenderAndInsert) {
                el = el.el; // legacy widget
            } else if (!(el instanceof HTMLElement)) {
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
    QUnit.assert.containsN = containsN;
    QUnit.assert.containsNone = containsNone;
    QUnit.assert.containsOnce = containsOnce;
    QUnit.assert.doesNotHaveClass = doesNotHaveClass;
    QUnit.assert.hasClass = hasClass;
    QUnit.assert.hasAttrValue = hasAttrValue;
    QUnit.assert.isVisible = isVisible;
    QUnit.assert.isNotVisible = isNotVisible;

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
        console.error(infos.map((info) => info.error || info).join("\n"));
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
     * Waits for the module system to end processing the JS modules, so that we can
     * make the suite fail if some modules couldn't be loaded (e.g. because of a
     * missing dependency).
     *
     * @returns {Promise<boolean>}
     */
    async function checkModules() {
        // do not mark the suite as successful already, as we still need to ensure
        // that all modules have been correctly loaded
        document.querySelector("#qunit-banner").classList.remove("qunit-pass");
        const modulesAlert = document.createElement("div");
        modulesAlert.classList.add("alert");
        modulesAlert.classList.add("alert-info");
        modulesAlert.textContent = "Waiting for modules check...";
        document.getElementById("qunit").appendChild(modulesAlert);
        const info = odoo.__DEBUG__.jsModules;
        if (info.missing.length || info.failed.length || info.unloaded.length) {
            document.querySelector("#qunit-banner").classList.add("qunit-fail");
            modulesAlert.classList.toggle("alert-danger");
            modulesAlert.classList.toggle("alert-info");
            let error = "Some modules couldn't be started:<ul>";
            if (info.failed.length) {
                const failedList = info.failed.map((mod) => "<li>" + _.escape(mod) + "</li>");
                error += `<li> Failed modules: <ul>${failedList.join("")}</ul> </li>`;
            }
            if (info.missing.length) {
                const missingList = info.missing.map((mod) => "<li>" + _.escape(mod) + "</li>");
                error += `<li> Missing dependencies: <ul>${missingList.join("")}</ul> </li>`;
            }
            if (info.unloaded.length) {
                const unloadedList = info.unloaded.map((mod) => "<li>" + _.escape(mod) + "</li>");
                error += `
                    <li> Non loaded modules due to missing dependencies:
                        <ul>${unloadedList.join("")}</ul>
                    </li>`;
                if (info.cycle) {
                    error += `<li> Cycle: ${info.cycle} </li>`;
                }
            }
            error += "</ul>";

            modulesAlert.innerHTML = error;
            errorMessages.unshift(error);
            return false;
        } else {
            modulesAlert.classList.toggle("alert-success");
            modulesAlert.classList.toggle("alert-info");
            modulesAlert.textContent = "All modules have been correctly loaded.";
            document.querySelector("#qunit-banner").classList.add("qunit-pass");
            return true;
        }
    }

    QUnit.begin(() => odoo.__DEBUG__.didLogInfo);
    /**
     * If we want to log several errors, we have to log all of them at once, as
     * browser_js is closed as soon as an error is logged.
     */
    QUnit.done(async (result) => {
        const allModulesLoaded = await checkModules();
        if (result.failed) {
            errorMessages.push(`${result.failed} / ${result.total} tests failed.`);
        }
        if (!result.failed && allModulesLoaded) {
            console.log("test successful");
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
        const location = window.location;
        reRunDebug.setAttribute(
            "href",
            `${location.origin}${location.pathname}${location.search}&debugTestId=${testId}`
        );

        reRun.parentElement.insertBefore(reRunDebug, reRun.nextSibling);
    });

    const debugTestId = new URLSearchParams(location.search).get("debugTestId");
    if (debugTestId) {
        QUnit.config.testId = [debugTestId];
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
    const oldError = QUnit.onError;
    QUnit.onError = (err) => {
        if (err.message === "ResizeObserver loop limit exceeded") {
            return true;
        }
        return oldError(err);
    };

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
    function insertStats() {
        const toolbar = document.querySelector("#qunit-testrunner-toolbar .qunit-url-config");
        const statsEl = document.createElement("label");
        passedEl = document.createElement("span");
        passedEl.classList.add("text-success", "ms-5", "me-3");
        statsEl.appendChild(passedEl);
        failedEl = document.createElement("span");
        failedEl.classList.add("text-danger", "me-3");
        statsEl.appendChild(failedEl);
        skippedEl = document.createElement("span");
        skippedEl.classList.add("text-dark");
        statsEl.appendChild(skippedEl);
        toolbar.appendChild(statsEl);
    }

    let testPassedCount = 0;
    let testFailedCount = 0;
    let testSkippedCount = 0;
    QUnit.testDone(({ skipped, failed }) => {
        if (!passedEl) {
            insertStats();
        }
        if (!skipped) {
            if (failed > 0) {
                testFailedCount++;
            } else {
                testPassedCount++;
            }
        } else {
            testSkippedCount++;
        }
        passedEl.innerText = `${testPassedCount} passed`;
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

    const { onUnhandledRejection, onError } = QUnit;
    QUnit.onUnhandledRejection = () => {};
    QUnit.onError = () => {};
    window.addEventListener("error", async (ev) => {
        // don't do anything if error service is up and we are in a test
        if (registry.category("services").get("error", false) && QUnit.config.current) {
            return;
        }
        // Do not log to the console as this will kill python test early
        ev.preventDefault();
        const { error: originalError } = ev;
        const uncaughtError = new UncaughtClientError();
        if (originalError instanceof Error) {
            originalError.errorEvent = ev;
            await completeUncaughtError(uncaughtError, originalError);
            originalError.stacktrace = uncaughtError.traceback;
        }
        onError(originalError);
    });

    window.addEventListener("unhandledrejection", async (ev) => {
        // don't do anything if error service is up and we are in a test
        if (registry.category("services").get("error", false) && QUnit.config.current) {
            return;
        }
        // Do not log to the console as this will kill python test early
        ev.preventDefault();
        const originalError = ev.reason;
        const uncaughtError = new UncaughtPromiseError();
        uncaughtError.unhandledRejectionEvent = ev;
        if (originalError instanceof Error) {
            originalError.errorEvent = ev;
            await completeUncaughtError(uncaughtError, originalError);
            originalError.stack = uncaughtError.traceback;
        }
        onUnhandledRejection(originalError);
    });
}
