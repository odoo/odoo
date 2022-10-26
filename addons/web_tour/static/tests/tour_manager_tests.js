odoo.define('web_tour.tour_manager_tests', async function (require) {
    "use strict";

    const core = require("web.core");
    const KanbanView = require('web.KanbanView');
    const TourManager = require('web_tour.TourManager');
    const testUtils = require('web.test_utils');
    const createView = testUtils.createView;

    /**
     * Create a widget and a TourManager instance with a list of given Tour objects.
     * @see `TourManager.register()` for more details on the Tours registry system.
     * @param {Object} params aside from the parameters defined below, passed
     *                        to {@see addMockEnvironment}.
     * @param {string[]} [params.consumed_tours]
     * @param {boolean} [params.debug] also passed along
     * @param {boolean} [params.disabled]
     * @param {string} params.template inner HTML content of the widget
     * @param {Object[]} params.tours { {string} name, {Object} option, {Object[]} steps }
     */
    async function createTourManager({ consumed_tours, disabled, template, tours, ...params }) {
        const parent = await testUtils.createParent(params);
        const tourManager = new TourManager(parent, consumed_tours, disabled);
        tourManager.running_step_delay = 0;
        for (const { name, options, steps } of tours) {
            tourManager.register(name, options, steps);
        }
        const _destroy = tourManager.destroy;
        tourManager.destroy = function () {
            tourManager.destroy = _destroy;
            parent.destroy();
        };
        await parent.prependTo(testUtils.prepareTarget(params.debug));
        parent.el.innerHTML = template;
        await tourManager._register_all(true);
        // Wait for possible tooltips to be loaded and appended.
        await testUtils.nextTick();
        return tourManager;
    }

    QUnit.module("Tours", function () {

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

            assert.containsOnce(document.body, '.o_tooltip:visible');
            assert.strictEqual($('.o_tooltip_content:visible').text(), "Oui",
                "content should be that of the third tour");

            tourManager.destroy();
        });

        QUnit.test("Displays a rainbow man by default at the end of tours", async function (assert) {
            assert.expect(3);

            function onShowEffect(params) {
                assert.deepEqual(params, {
                    fadeout: "medium",
                    message: owl.markup("<strong><b>Good job!</b> You went through all steps of this tour.</strong>"),
                    type: "rainbow_man"
                });
            }
            core.bus.on("show-effect", null, onShowEffect);

            const tourManager = await createTourManager({
                data: { 'web_tour.tour': {  fields: {}, consume() {} } },
                template: `<button class="btn anchor">Anchor</button>`,
                tours: [{
                    name: "Some tour",
                    options: {},
                    steps: [{ trigger: '.anchor', content: "anchor" }],
                }],
                // Use this test in "debug" mode because the tips need to be in
                // the viewport to be able to test their normal content
                // (otherwise, the tips would indicate to the users that they
                // have to scroll).
                debug: true,
            });

            assert.containsOnce(document.body, '.o_tooltip');
            await testUtils.dom.click($('.anchor'));
            assert.containsNone(document.body, '.o_tooltip');

            tourManager.destroy();
            core.bus.off("show-effect", onShowEffect);
        });

        QUnit.test("Click on invisible tip consumes it", async function (assert) {
            assert.expect(5);

            const tourManager = await createTourManager({
                data: { 'web_tour.tour': {  fields: {}, consume() {} } },
                template: `
                    <button class="btn anchor1">Anchor</button>
                    <button class="btn anchor2">Anchor</button>
                    `,
                tours: [{
                    name: "Tour 1",
                    options: { rainbowMan: false, sequence: 10 },
                    steps: [{ trigger: '.anchor1', content: "1" }],
                }, {
                    name: "Tour 2",
                    options: { rainbowMan: false, sequence: 5 },
                    steps: [{ trigger: '.anchor2', content: "2" }],
                }],
                // Use this test in "debug" mode because the tips need to be in
                // the viewport to be able to test their normal content
                // (otherwise, the tips would indicate to the users that they
                // have to scroll).
                debug: true,
            });

            assert.containsN(document.body, '.o_tooltip', 2);
            assert.strictEqual($('.o_tooltip_content:visible').text(), "2");

            await testUtils.dom.click($('.anchor1'));
            assert.containsOnce(document.body, '.o_tooltip');
            assert.strictEqual($('.o_tooltip_content:visible').text(), "2");

            await testUtils.dom.click($('.anchor2'));
            assert.containsNone(document.body, '.o_tooltip');

            tourManager.destroy();
        });

        QUnit.test("Step anchor replaced", async function (assert) {
            assert.expect(3);

            const tourManager = await createTourManager({
                observe: true,
                template: `<input class="anchor"/>`,
                tours: [{
                    name: "Tour",
                    options: { rainbowMan: false },
                    steps: [{ trigger: "input.anchor" }],
                }],
            });

            assert.containsOnce(document.body, '.o_tooltip:visible');


            const $anchor = $(".anchor");
            const $parent = $anchor.parent();
            $parent.empty();
            $parent.append($anchor);
            // Simulates the observer picking up the mutation and triggering an update
            tourManager.update();
            await testUtils.nextTick();

            assert.containsOnce(document.body, '.o_tooltip:visible');

            await testUtils.fields.editInput($('.anchor'), "AAA");

            assert.containsNone(document.body, '.o_tooltip:visible');

            tourManager.destroy();
        });

        QUnit.test("kanban quick create VS tour tooltips", async function (assert) {
            assert.expect(3);

            const kanban = await createView({
                View: KanbanView,
                model: 'partner',
                data: {
                    partner: {
                        fields: {
                            foo: {string: "Foo", type: "char"},
                            bar: {string: "Bar", type: "boolean"},
                        },
                        records: [
                            {id: 1, bar: true, foo: "yop"},
                        ]
                    }
                },
                arch: `<kanban>
                        <field name="bar"/>
                        <templates><t t-name="kanban-box">
                            <div><field name="foo"/></div>
                        </t></templates>
                        </kanban>`,
                groupBy: ['bar'],
            });

            // click to add an element
            await testUtils.dom.click(kanban.$('.o_kanban_header .o_kanban_quick_add i').first());
            assert.containsOnce(kanban, '.o_kanban_quick_create',
                "should have open the quick create widget");

            // create tour manager targeting the kanban quick create in its steps
            const tourManager = await createTourManager({
                observe: true,
                template: kanban.$el.html(),
                tours: [{
                    name: "Tour",
                    options: { rainbowMan: false },
                    steps: [{ trigger: "input[name='display_name']" }],
                }],
            });

            assert.containsOnce(document.body, '.o_tooltip:visible');

            await testUtils.dom.click($('.o_tooltip:visible'));
            assert.containsOnce(kanban, '.o_kanban_quick_create',
                "the quick create should not have been destroyed when tooltip is clicked");

            kanban.destroy();
            tourManager.destroy();
        });

        QUnit.test("Automatic tour disabling", async function (assert) {
            assert.expect(2);

            const options = {
                template: `<button class="btn anchor">Anchor</button>`,
                tours: [{ name: "Tour", options: {}, steps: [{ trigger: '.anchor' }] }],
            };

            const enabledTM = await createTourManager({ disabled: false, ...options });

            assert.containsOnce(document.body, '.o_tooltip:visible');

            enabledTM.destroy();

            const disabledTM = await createTourManager({ disabled: true, ...options });

            assert.containsNone(document.body, '.o_tooltip:visible');

            disabledTM.destroy();
        });
    });
});
