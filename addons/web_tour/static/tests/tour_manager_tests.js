odoo.define('web_tour.tour_manager_tests', async function (require) {
    "use strict";

    const TourManager = require('web_tour.TourManager');
    const testUtils = require('web.test_utils');

    const ajax = require('web.ajax');
    const { qweb } = require('web.core');

    // Pre-load the Tip widget template
    await ajax.loadXML('/web_tour/static/src/xml/tip.xml', qweb);

    /**
     * Create a widget and a TourManager instance with a list of given Tour objects.
     * @see TourManager.register() for more details on the Tours registry system.
     * @param {Object} params
     * @param {string[]} [params.consumed_tours]
     * @param {boolean} [params.debug]
     * @param {string} params.template inner HTML content of the widget
     * @param {Object[]} params.tours { {string} name, {Object} option, {Object[]} steps }
     */
    async function createTourManager({ consumed_tours, debug, template, tours }) {
        const parent = testUtils.createParent({ debug });
        const tourManager = new TourManager(parent, consumed_tours);
        tourManager.running_step_delay = 0;
        for (const { name, options, steps } of tours) {
            tourManager.register(name, options, steps);
        }
        const _destroy = tourManager.destroy;
        tourManager.destroy = function () {
            tourManager.destroy = _destroy;
            parent.destroy();
        };
        await parent.prependTo(testUtils.prepareTarget(debug));
        parent.el.innerHTML = template;
        testUtils.mock.patch(TourManager, {
            // Since the `tour_disable.js` script automatically sets tours as consumed
            // as soon as they are registered, we override the "is consumed" to
            // assert that the tour is in the `consumed_tours` param key.
            _isTourConsumed: name => (consumed_tours || []).includes(name),
        });
        await tourManager._register_all(true);
        // Wait for possible tooltips to be loaded and appended.
        await testUtils.nextTick();
        return tourManager;
    }

    QUnit.module("Tours", {
        afterEach() {
            testUtils.mock.unpatch(TourManager);
        },
    }, function () {

        QUnit.module("Tour manager");

        QUnit.test("Tours sequence", async function (assert) {
            assert.expect(2);

            const tourManager = await createTourManager({
                template: `
                    <button class="btn anchor">Anchor</button>`,
                tours: [
                    { name: "Tour 1", options: { sequence: 10 }, steps: [{ trigger: '.anchor' }] },
                    { name: "Tour 2", options: {}, steps: [{ trigger: '.anchor' }] },
                    { name: "Tour 3", options: { sequence: 5 }, steps: [{ trigger: '.anchor', content: "Oui" }] },
                ],
                // Use this test in "debug" mode because the tips need to be in
                // the viewport to be able to test their normal content
                // (otherwise, the tips would indicate to the users that they
                // have to scroll).
                debug: true,
            });

            assert.containsOnce(document.body, '.o_tooltip');
            const tooltip = document.querySelector('.o_tooltip_content');
            assert.strictEqual(tooltip.innerHTML.trim(), "Oui",
                "content should be that of the third tour");

            tourManager.destroy();
        });
    });
});
