odoo.define("hr_timesheet.timesheet_uom_tests_env", function (require) {
"use strict";

const session = require('web.session');
const { createView } = require("web.test_utils");
const ListView = require('web.ListView');
const { timesheetUomService } = require('hr_timesheet.timesheet_uom');
const { makeTestEnv } = require("@web/../tests/helpers/mock_env");
const { registry } = require("@web/core/registry");

/**
 * Sets the timesheet related widgets testing environment up.
 */
function SetupTimesheetUOMWidgetsTestEnvironment () {
    this.allowedCompanies = {
        1: {
            id: 1,
            name: 'Company 1',
            timesheet_uom_id: 1,
            timesheet_uom_factor: 1,
        },
        2: {
            id: 2,
            name: 'Company 2',
            timesheet_uom_id: 2,
            timesheet_uom_factor: 0.125,
        },
        3: {
            id: 3,
            name: 'Company 3',
            timesheet_uom_id: 2,
            timesheet_uom_factor: 0.125,
        },
    };
    this.uomIds = {
        1: {
            id: 1,
            name: 'hour',
            rounding: 0.01,
            timesheet_widget: 'float_time',
        },
        2: {
            id: 2,
            name: 'day',
            rounding: 0.01,
            timesheet_widget: 'float_toggle',
        },
    };
    this.singleCompanyHourUOMUser = {
        allowed_company_ids: [this.allowedCompanies[1].id],
    };
    this.singleCompanyDayUOMUser = {
        allowed_company_ids: [this.allowedCompanies[2].id],
    };
    this.multiCompanyHourUOMUser = {
        allowed_company_ids: [
            this.allowedCompanies[1].id,
            this.allowedCompanies[3].id,
        ],
    };
    this.multiCompanyDayUOMUser = {
        allowed_company_ids: [
            this.allowedCompanies[3].id,
            this.allowedCompanies[1].id,
        ],
    };
    this.session = {
        uid: 0, // In order to avoid bbqState and cookies to be taken into account in AbstractWebClient.
        user_companies: {
            current_company: 1,
            allowed_companies: this.allowedCompanies,
        },
        user_context: this.singleCompanyHourUOMUser,
        uom_ids: this.uomIds,
    };
    this.data = {
        'account.analytic.line': {
            fields: {
                project_id: {
                    string: "Project",
                    type: "many2one",
                    relation: "project.project",
                },
                task_id: {
                    string:"Task",
                    type: "many2one",
                    relation: "project.task",
                },
                date: {
                    string: "Date",
                    type: "date",
                },
                unit_amount: {
                    string: "Unit Amount",
                    type: "float",
                },
            },
            records: [
                {
                    id: 1,
                    project_id: 1,
                    task_id: 1,
                    date: "2021-01-12",
                    unit_amount: 8,
                },
            ],
        },
        'project.project': {
            fields: {
                name: {
                    string: "Project Name",
                    type: "char",
                },
            },
            records: [
                {
                    id: 1,
                    display_name: "P1",
                },
            ],
        },
        'project.task': {
            fields: {
                name: {
                    string: "Task Name",
                    type: "char",
                },
                project_id: {
                    string: "Project",
                    type: "many2one",
                    relation: "project.project",
                },
            },
            records: [
                {
                    id: 1,
                    display_name: "T1",
                    project_id: 1,
                },
            ],
        },
    };
    this.patchSessionAndStartServices = async function (sessionToApply, doNotUseEnvSession = false) {
        /*
        Adds the timesheet_uom to the fieldRegistry by setting the session and
        starting the timesheet_uom service which registers the widget in the registry.
        */
        session.user_companies = Object.assign(
            { },
            !doNotUseEnvSession && this.session.user_companies || { },
            sessionToApply && sessionToApply.user_companies);
        if (Object.keys(session.user_companies).length === 0) {
            delete session.user_companies;
        }
        session.user_context = Object.assign(
            { },
            !doNotUseEnvSession && this.session.user_context || { },
            sessionToApply && sessionToApply.user_context);
        session.uom_ids = Object.assign(
            { },
            !doNotUseEnvSession && this.session.uom_ids || { },
            sessionToApply && sessionToApply.uom_ids);
        if (!doNotUseEnvSession && 'uid' in this.session) {
            session.uid = this.session.uid;
        }
        if (sessionToApply && 'uid' in sessionToApply) {
            session.uid = sessionToApply.uid;
        }
        const serviceRegistry = registry.category("services");
        if (!serviceRegistry.contains("legacy_timesheet_uom")) {
            // Remove dependency on legacy_session since we're patching the session directly
            serviceRegistry.add("legacy_timesheet_uom", Object.assign({}, timesheetUomService, { dependencies: [] }));
        }
        await makeTestEnv(); // Start services
    };
    this.createView = async function (options) {
        const sessionToApply = options && options.session || { };
        await this.patchSessionAndStartServices(sessionToApply);
        return await createView(Object.assign(
            {
                View: ListView,
                data: this.data,
                model: 'account.analytic.line',
                arch: `
                    <tree>
                        <field name="unit_amount" widget="timesheet_uom"/>
                    </tree>`,
            },
            options || { },
        ));
    };
};

return SetupTimesheetUOMWidgetsTestEnvironment;

});
