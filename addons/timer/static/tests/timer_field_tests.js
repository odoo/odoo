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
                    // action_timer_resume: { string: "action_timer_resume" },
                    // display_name: { string: "Displayed name", type: "text" },
                    // display_timer_start_secondary: { string: "action_timer_start" },
                },
                records: [{
                    id: 1,
                    // display_timer_pause: false,
                    // display_timer_resume: false,
                    // display_timer_start_secondary: true,
                    // display_timer_stop: false,
                    // display_timesheet_timer: true,
                    timer_start: "2020-01-01 00:00:00",
                    timer_stop: false,
                    timer_pause: false,
                }],
            },
        };
    }
}, function () {
    QUnit.module('timer.timer');

    QUnit.only('timer_toggle_button: basic rendering', async function (assert) {
        assert.expect(2);

        this.data.partner.fields.is_timer_running = {string: 'Is Timer Running', type: 'boolean', default: false};
        this.data.partner.fields.value = {string: 'value', type: 'boolean', default: false};

        const kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            debug: true,
            arch: `<kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="value"/>
                                <field name="is_timer_running" widget="timer_toggle_button" options="{\'prevent_deletion\': True}"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            res_id: 1,
            mockRPC: function (route, args) {
                if (route === '/web/dataset/call_kw/partner/action_timer_start') {debugger
                    this.data.partner.records[0].is_timer_running = true;
                    return Promise.resolve();
                }
                if (route === '/web/dataset/call_kw/partner/action_timer_stop') {debugger
                    this.data.partner.records[0].is_timer_running = false;
                    return Promise.resolve();
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.containsOnce(kanban, 'button.o-timer-button',
            "should have timer_toggle_button widget");
        await testUtils.dom.click(kanban.el.querySelector('.o_icon_button'));
        assert.containsOnce(kanban, 'i.fa-stop-circle',
            "should have stop icon");

        kanban.destroy();
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
