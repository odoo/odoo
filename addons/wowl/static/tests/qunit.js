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
    if (target instanceof Component) {
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
   * @param {HTMLElement} el
   * @param {string} classNames
   * @param {boolean} shouldHaveClass
   * @param {string} [msg]
   */
  function _checkClass(el, classNames, shouldHaveClass, msg) {
    msg = msg || `target should ${shouldHaveClass ? "have" : "not have"} classnames ${classNames}`;
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
   * Helper function, to check if a given element
   * - is unique (if it is a jquery node set)
   * - is (or not) visible
   *
   * @private
   * @param {HTMLElement} el
   * @param {boolean} shouldBeVisible
   * @param {string} [msg]
   */
  function _checkVisible(el, shouldBeVisible, msg) {
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
    return true; // TODO: unskip this
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
    if (info.missing.length || info.failed.length) {
      document.querySelector("#qunit-banner").classList.add("qunit-fail");
      modulesAlert.classList.toggle("alert-danger");
      modulesAlert.classList.toggle("alert-info");
      const failingModules = info.missing.concat(info.failed);
      const error = `Some modules couldn't be started: ${failingModules.join(", ")}.`;
      modulesAlert.textContent = error;
      errorMessages.unshift(error);
      return false;
    } else {
      modulesAlert.classList.toggle("alert-danger");
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
    let info = '"QUnit test failed: "'; // + result.module + ' > ' + result.name + '"';
    info += ' [message: "' + result.message + '"';
    if (result.actual !== null) {
      info += ', actual: "' + result.actual + '"';
    }
    if (result.expected !== null) {
      info += ', expected: "' + result.expected + '"';
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
  // Check leftovers
  // -----------------------------------------------------------------------------
  /**
   * List of elements tolerated in the body after a test. The property "keep"
   * prevents the element from being removed (typically: qunit suite elements).
   */
  const validElements = [
    // always in the body:
    { tagName: "DIV", attr: "id", value: "qunit", keep: true },
    { tagName: "DIV", attr: "id", value: "qunit-fixture", keep: true },
    // shouldn't be in the body after a test but are tolerated:
    { tagName: "SCRIPT", attr: "id", value: "" },
    { tagName: "DIV", attr: "class", value: "o_notification_manager" },
    { tagName: "DIV", attr: "class", value: "tooltip fade bs-tooltip-auto" },
    { tagName: "DIV", attr: "class", value: "tooltip fade bs-tooltip-auto show" },
    { tagName: "SPAN", attr: "class", value: "select2-hidden-accessible" },
    // Due to a Document Kanban bug (already present in 12.0)
    { tagName: "DIV", attr: "class", value: "ui-helper-hidden-accessible" },
    {
      tagName: "UL",
      attr: "class",
      value: "ui-menu ui-widget ui-widget-content ui-autocomplete ui-front",
    },
  ];
  /**
   * After each test, we check that there is no leftover in the DOM.
   *
   * Note: this event is not QUnit standard, we added it for this specific use case.
   * As a payload, an object with keys 'moduleName' and 'testName' is provided. It
   * is used to indicate the test that left elements in the DOM, when it happens.
   */
  QUnit.on("OdooAfterTestHook", function (info) {
    const toRemove = [];
    // check for leftover elements in the body
    for (const bodyChild of document.body.children) {
      const tolerated = validElements.find(
        (e) => e.tagName === bodyChild.tagName && bodyChild.getAttribute(e.attr) === e.value
      );
      if (!tolerated) {
        console.error(`Test ${info.moduleName} > ${info.testName}`);
        console.error(
          "Body still contains undesirable elements:" + "\nInvalid element:\n" + bodyChild.outerHTML
        );
        QUnit.pushFailure(`Body still contains undesirable elements`);
      }
      if (!tolerated || !tolerated.keep) {
        toRemove.push(bodyChild);
      }
    }
    // check for leftovers in #qunit-fixture
    const qunitFixture = document.getElementById("qunit-fixture");
    if (qunitFixture.children.length) {
      // console.error('#qunit-fixture still contains elements:' +
      //     '\n#qunit-fixture HTML:\n' + qunitFixture.outerHTML);
      // QUnit.pushFailure(`#qunit-fixture still contains elements`);
      toRemove.push(...qunitFixture.children);
    }
    // remove unwanted elements if not in debug
    if (!QUnit.config.debug) {
      for (const el of toRemove) {
        el.remove();
      }
      document.body.classList.remove("modal-open");
    }
  });
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
})();
