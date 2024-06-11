/** @odoo-module **/

// -----------------------------------------------------------------------------
// Cleanup
// -----------------------------------------------------------------------------

const cleanups = [];

/**
 * Register a cleanup callback that will be executed whenever the current test
 * is done.
 *
 * - the cleanups will be executed in reverse order
 * - they will be executed even if the test fails/crashes
 *
 * @param {Function} callback
 */
export function registerCleanup(callback) {
    cleanups.push(callback);
}

if (window.QUnit) {
    QUnit.on("OdooAfterTestHook", (info) => {
        if (QUnit.config.debug) {
            return;
        }
        let cleanup;
        // note that this calls the cleanup callbacks in reverse order!
        while ((cleanup = cleanups.pop())) {
            try {
                cleanup(info);
            } catch (error) {
                console.error(error);
            }
        }
    });

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
        { tagName: "DIV", attr: "class", value: "tooltip tooltip-field-info fade bs-tooltip-auto" },
        {
            tagName: "DIV",
            attr: "class",
            value: "tooltip tooltip-field-info fade bs-tooltip-auto show",
        },
        { tagName: "SPAN", attr: "class", value: "select2-hidden-accessible" },

        // Due to a Document Kanban bug (already present in 12.0)
        { tagName: "DIV", attr: "class", value: "ui-helper-hidden-accessible" },
        {
            tagName: "UL",
            attr: "class",
            value: "ui-menu ui-widget ui-widget-content ui-autocomplete ui-front",
        },
        {
            tagName: "UL",
            attr: "class",
            value: "ui-menu ui-widget ui-widget-content ui-autocomplete dropdown-menu ui-front", // many2ones
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
        if (QUnit.config.debug) {
            return;
        }
        const failed = info.testReport.getStatus() === "failed";
        const toRemove = [];
        // check for leftover elements in the body
        for (const bodyChild of document.body.children) {
            const tolerated = validElements.find(
                (e) => e.tagName === bodyChild.tagName && bodyChild.getAttribute(e.attr) === e.value
            );
            if (!failed && !tolerated) {
                QUnit.pushFailure(
                    `Body still contains undesirable elements:\n${bodyChild.outerHTML}`
                );
            }
            if (!tolerated || !tolerated.keep) {
                toRemove.push(bodyChild);
            }
        }
        // cleanup leftovers in #qunit-fixture
        const qunitFixture = document.getElementById("qunit-fixture");
        if (qunitFixture.children.length) {
            toRemove.push(...qunitFixture.children);
        }
        // remove unwanted elements if not in debug
        for (const el of toRemove) {
            el.remove();
        }
        document.body.classList.remove("modal-open");
    });
}
