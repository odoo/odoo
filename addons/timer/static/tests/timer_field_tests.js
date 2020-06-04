odoo.define('timer.timer_field', function (require) {
"use strict";

const FormView = require('web.FormView');
const KanbanView = require('web.KanbanView');
const testUtils = require('web.test_utils');

const createView = testUtils.createView;

QUnit.module('timer_timer', {
    beforeEach: function () {
        this.data = {
            partner: {
                fields: {
                    display_name: { string: "Displayed name", type: "text" },
                    display_timer_start_secondary: { string: "action_timer_start" },
                },
                records: [{
                    id: 1,
                    display_timer_pause: false,
                    display_timer_resume: false,
                    display_timer_start_secondary: true,
                    display_timer_stop: false,
                    display_timesheet_timer: true,
                    timer_start: false,
                    timer_pause: false,
                }],
            },
        };
    }
}, function () {
    QUnit.module('Timer');

    QUnit.test('timer_toggle_button: basic rendering', async function (assert) {
        assert.expect(1);

        this.data.partner.fields.is_timer_running = {string: 'Is Timer Running', type: 'boolean', default: false};

        const kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            debug: true,
            arch: `<kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="display_name" widget="timer_toggle_button"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            res_id: 1,
            mockRPC: function (route) {debugger
                if (route === '/web/dataset/call_kw/partner/action_timer_start') {debugger
                    this.data.partner.records[0].is_timer_running = true;
                }
                if (route === '/web/dataset/call_kw/partner/action_timer_stop') {debugger
                    this.data.partner.records[0].is_timer_running = false;
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.containsOnce(kanban, 'button.o-timer-button',
            "should have timer_toggle_button widget");
        await testUtils.dom.click(kanban.el.querySelector('.o_icon_button'));

        kanban.destroy();
    });

    // QUnit.only('timer button', async function (assert) {
    //     assert.expect(1);

    //     const form = await createView({
    //     View: FormView,
    //     model: 'partner',
    //     data: this.data,
    //     debug: true,
    //     arch: '<form>' +
    //                 '<div class="o_form_statusbar">' +
    //                     '<div class="o_statusbar_buttons">' +
    //                         '<button string="Start" name="action_timer_start" widget="timer_timer" class="btn btn-primary" type="object"/>' +
    //                     '</div>' +
    //                     '<field name="display_name" class="text-danger ml-auto h2 ml-4 font-weight-bold"/>' +
    //                 '</div>' +
    //             '</form>',
    //     res_id: 1,
    //     mockRPC: function (route, args) {debugger
    //             if (route = "/web/dataset/call_kw/partner/read") {
    //                 return Promise.resolve();
    //             }
    //             return this._super.apply(this, arguments);
    //         },
    // });
    // await testUtils.dom.click(form.el.querySelectorAll('button')[6]);

    // //form.destroy();
    // });
});
});