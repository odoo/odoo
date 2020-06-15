odoo.define('timer.timer_field', function (require) {
"use strict";

const concurrency = require('web.concurrency');
const FormView = require('web.FormView');
const KanbanView = require('web.KanbanView');
const testUtils = require('web.test_utils');

const createView = testUtils.createView;

QUnit.module('timer_timer', {
    beforeEach: function () {
        this.data = {
            partner: {
                fields: {
                    timer_start: { string: "timer start", type: "datetime" },
                    timer_stop: { string: "timer stop", type: "datetime" },
                    timer_pause: { string: "action_timer_pause", type: "datetime" },
                    is_timer_running: { string: "is timer running", type: "boolean" },
                },
                records: [{
                    id: 1,
                    timer_start: "2020-01-01 00:00:00",
                    timer_stop: false,
                    timer_pause: false,
                    is_timer_running: false,
                }],
            },
        };
    }
}, function () {
    QUnit.module('timer.timer');

    QUnit.test('timer_toggle_button: basic rendering', async function (assert) {
        assert.expect(3);

        const kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            debug: true,
            arch: `<kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="is_timer_running" widget="timer_toggle_button" options="{\'prevent_deletion\': True}"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            res_id: 1,
        });

        assert.containsOnce(kanban, 'button.o-timer-button',
            "should have timer_toggle_button widget");
        assert.containsOnce(kanban, 'i.fa-play-circle',
                "should have play icon");

        return concurrency.delay(1000).then(async () => {
            this.data.partner.records[0].is_timer_running = "false";
            await kanban.reload();
            return concurrency.delay(1000);
        }).then(() => {
            assert.containsOnce(kanban, 'i.fa-stop-circle',
                "should have stop icon");

            kanban.destroy();
        });
    });

    QUnit.test('timer field widget: basic rendering', async function (assert) {
        assert.expect(4);

        const form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: `<form>
                    <div class="o_form_statusbar">
                        <field name="timer_pause" invisible="1" />
                        <field name="timer_start" widget="timer_timer" class="text-danger ml-auto h2 ml-4 font-weight-bold" />
                    </div>
                </form>`,
            res_id: 1,
            mockRPC: function (route, args) {
                if (args.method === "get_server_time") {
                    return Promise.resolve("2020-01-01 00:00:00");
                }
                return this._super.apply(this, arguments);
            },
        });

        await testUtils.nextTick();
        assert.containsOnce(form, "div[name='timer_start']",
            "should have timer widget");
        assert.hasClass(form.$("div[name='timer_start']"), "text-danger",
            "should have text-danger class on timer widget");

        return concurrency.delay(1000).then(async () => {
            assert.strictEqual(form.$("div[name='timer_start']").text(), "00:00:01",
                "should have pouse time widget");
            this.data.partner.records[0].timer_pause = "2020-01-01 01:00:00";
            await form.reload();
            return concurrency.delay(1000);
        }).then(() => {
            assert.strictEqual(form.$("div[name='timer_start']").text(), "01:00:00",
                "should have pouse time widget");

            form.destroy();
        });
    });
});
});
