odoo.define("hr_timesheet.timesheet_uom_tests", function (require) {
"use strict";

const session = require('web.session');
const SetupTimesheetUOMWidgetsTestEnvironment = require('hr_timesheet.timesheet_uom_tests_env');
const fieldUtils = require('web.field_utils');
const TimesheetUOM = require('hr_timesheet.timesheet_uom');

QUnit.module('Timesheet UOM Widgets', function (hooks) {
    let env;
    let sessionUserCompaniesBackup;
    let sessionUserContextBackup;
    let sessionUOMIdsBackup;
    let sessionUIDBackup;
    hooks.beforeEach(async function (assert) {
        env = new SetupTimesheetUOMWidgetsTestEnvironment();
        // Backups session parts that this testing module will alter in order to restore it at the end.
        sessionUserCompaniesBackup = session.user_companies || false;
        sessionUserContextBackup = session.user_context || false;
        sessionUOMIdsBackup = session.uom_ids || false;
        sessionUIDBackup = session.uid || false;
    });
    hooks.afterEach(async function (assert) {
        // Restores the session
        const sessionToApply = Object.assign(
            { },
            sessionUserCompaniesBackup && {
                user_companies: sessionUserCompaniesBackup,
            } || { },
            sessionUserContextBackup && {
                user_context: sessionUserContextBackup,
            } || { },
            sessionUOMIdsBackup && {
                uom_ids: sessionUOMIdsBackup,
            } || { },
            sessionUIDBackup && {
                uid: sessionUIDBackup,
            } || { });
        await env.patchSessionAndStartServices(sessionToApply, true);
    });
    QUnit.module('timesheet_uom', function (hooks) {
        QUnit.module('fieldRegistry', function (hooks) {
            let FieldTimesheetTimeBackup;
            let FieldTimesheetToggleBackup;
            hooks.beforeEach(function (assert) {
                // Backups the FieldTimesheetTime widget as it will be altered in this testing module
                // in order to to ease testing.
                FieldTimesheetTimeBackup = TimesheetUOM.FieldTimesheetTime;
                TimesheetUOM.FieldTimesheetTime.include({
                    _render: function () {
                        const $widgetIdentification = $('<div>').addClass('i_am_a_timesheet_time_widget');
                        this.$el.append($widgetIdentification);
                    },
                });
                FieldTimesheetToggleBackup = TimesheetUOM.FieldTimesheetToggle;
                TimesheetUOM.FieldTimesheetToggle.include({
                    _render: function () {
                        const $widgetIdentification = $('<div>').addClass('i_am_a_timesheet_toggle_widget');
                        this.$el.append($widgetIdentification);
                    },
                });
            });
            hooks.afterEach(async function (hooks) {
                // Restores the widgets and trigger reload in FieldRegistry.
                TimesheetUOM.FieldTimesheetTime = FieldTimesheetTimeBackup;
                TimesheetUOM.FieldTimesheetToggle = FieldTimesheetToggleBackup;
                await env.patchSessionAndStartServices({ }, true);
            });
            QUnit.test('the timesheet_uom widget added to the fieldRegistry is company related', async function (assert) {
                assert.expect(2);

                let view = await env.createView();
                assert.ok(view.$('.i_am_a_timesheet_time_widget').length, 'FieldTimesheetTime is rendered when company uom is hour');
                view.destroy();

                let option = {
                    session: {
                        user_context: env.singleCompanyDayUOMUser,
                    },
                };
                view = await env.createView(option);
                assert.ok(view.$('.i_am_a_timesheet_toggle_widget').length, 'FieldTimesheetToggle is rendered when company uom is day');
                view.destroy();
            });
            QUnit.test('the timesheet_uom widget added to the fieldRegistry in a multi company environment is the current company', async function (assert) {
                assert.expect(2);

                let option = {
                    session: {
                        user_context: env.multiCompanyHourUOMUser,
                    },
                };
                let view = await env.createView(option);
                assert.ok(view.$('.i_am_a_timesheet_time_widget').length, 'FieldTimesheetTime is rendered when current company uom is hour');
                view.destroy();

                option = {
                    session: {
                        user_context: env.multiCompanyDayUOMUser,
                    },
                };
                view = await env.createView(option);
                assert.ok(view.$('.i_am_a_timesheet_toggle_widget').length, 'FieldTimesheetToggle is rendered when current company uom is day');
                view.destroy();
            });
        });
        QUnit.module('timesheet_uom_factor', function (hooks) {
            QUnit.test('the timesheet_uom_factor usage in formatters and parsers is company related', async function (assert) {
                assert.expect(4);

                await env.patchSessionAndStartServices();
                assert.strictEqual(fieldUtils.format.timesheet_uom(1), '01:00', 'The format is taking the timesheet_uom_factor into account');
                assert.strictEqual(fieldUtils.parse.timesheet_uom('01:00'), 1, 'The parsing is taking the timesheet_uom_factor into account');

                const sessionToApply = {
                    user_context: env.singleCompanyDayUOMUser,
                };
                await env.patchSessionAndStartServices(sessionToApply);
                assert.strictEqual(fieldUtils.format.timesheet_uom(8), '1.00', 'The format is taking the timesheet_uom_factor into account');
                assert.strictEqual(fieldUtils.parse.timesheet_uom('1.00'), 8, 'The parsing is taking the timesheet_uom_factor into account');
            });
            QUnit.test('the timesheet_uom_factor taken into account in a multi company environment is the current company', async function (assert) {
                assert.expect(4);

                let sessionToApply = {
                    user_context: env.multiCompanyHourUOMUser,
                };
                await env.patchSessionAndStartServices(sessionToApply);
                assert.strictEqual(fieldUtils.format.timesheet_uom(1), '01:00', 'The format is taking the timesheet_uom_factor into account');
                assert.strictEqual(fieldUtils.parse.timesheet_uom('01:00'), 1, 'The parsing is taking the timesheet_uom_factor into account');

                sessionToApply.user_context = env.singleCompanyDayUOMUser;
                await env.patchSessionAndStartServices(sessionToApply);
                assert.strictEqual(fieldUtils.format.timesheet_uom(8), '1.00', 'The format is taking the timesheet_uom_factor into account');
                assert.strictEqual(fieldUtils.parse.timesheet_uom('1.00'), 8, 'The parsing is taking the timesheet_uom_factor into account');
            });
        });
    });
});
});
