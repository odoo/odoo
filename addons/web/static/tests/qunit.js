(function () {
    "use strict";

    const { Component } = owl;

    // -----------------------------------------------------------------------------
    // QUnit config
    // -----------------------------------------------------------------------------
    QUnit.config.autostart = false;
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
     * @param {Widget|jQuery|HTMLElement|owl.Component} w
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
        let isVisible = el && el.offsetWidth && el.offsetHeight;
        if (isVisible) {
            // This computation is a little more heavy and we only want to perform it
            // if the above assertion has failed.
            const rect = el.getBoundingClientRect();
            isVisible = rect.width + rect.height;
        }
        const condition = shouldBeVisible ? isVisible : !isVisible;
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
    const errorMessages = [];

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
        // wait for the module system to end processing the JS modules
        await odoo.__DEBUG__.didLogInfo;
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
            console.error(errorMessages.join("\n"));
        }
    });

    /**
     * This is done mostly for the .txt log file generated by the runbot.
     */
    QUnit.moduleDone((result) => {
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
        let info = `QUnit test failed: ${result.module} > ${result.name}`;
        info += ` [message: "${result.message}"`;
        if (result.actual !== null) {
            info += `, actual: "${result.actual}"`;
        }
        if (result.expected !== null) {
            info += `, expected: "${result.expected}"`;
        }
        info += "]";
        errorMessages.push(info);
    });

    QUnit.debug = (name, cb) => {
        QUnit.config.debug = true;
        QUnit.only(name, cb);
    };

    // Override global UnhandledRejection that is assigned wayyy before this file
    // Do not really crash on non-errors rejections
    const qunitUnhandledReject = QUnit.onUnhandledRejection;
    QUnit.onUnhandledRejection = (reason) => {
        if (reason instanceof Error) {
            qunitUnhandledReject(reason);
        }
    };

    // Essentially prevents default error logging when the rejection was
    // not due to an actual error
    const windowUnhandledReject = window.onunhandledrejection;
    window.onunhandledrejection = (ev) => {
        if (!(ev.reason instanceof Error)) {
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
        if (odoo.__DEBUG__.services["@web/core/errors/error_utils"]) {
            const errorUtils = odoo.__DEBUG__.services["@web/core/errors/error_utils"];
            const { annotateTraceback } = errorUtils;
            QUnit.annotateTraceback = annotateTraceback;
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
    QUnit.onError = err => {
        if (err.message === 'ResizeObserver loop limit exceeded') {
            return true;
        }
        return oldError(err);
    }

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
})();
