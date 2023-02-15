/** @odoo-module */

import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { companyService } from "@web/webclient/company_service";

import { patchWithCleanup } from "@web/../tests/helpers/utils";
import { setupViewRegistries } from "@web/../tests/views/helpers";


export const getServerData = () => JSON.parse(JSON.stringify({
    models: {
        'account.analytic.line': {
            fields: {
                project_id: { string: "Project", type: "many2one", relation: "project.project" },
                task_id: { string: "Task", type: "many2one", relation: "project.task" },
                unit_amount: { string: "Unit Amount", type: "integer" },
            },
            records: [
                { id: 1, project_id: 1, task_id: 3, unit_amount: 1 },
                { id: 2, project_id: 1, task_id: false, unit_amount: 1 },
                { id: 3, project_id: false, task_id: false, unit_amount: 1 },
            ],
        },
        'project.project': {
            fields: {
                name: { string: "Name", type: "string" },
            },
            records: [
                { id: 1, name: "Project 1" },
            ],
        },
        'project.task': {
            fields: {
                name: { string: "Name", type: "string" },
                project_id: { string: "Project", type: "many2one", relation: "project.project" },
            },
            records: [
                { id: 1, name: "Task 1\u00A0AdditionalInfo", project_id: 1 },
                { id: 2, name: "Task 2\u00A0AdditionalInfo", project_id: 1 },
                { id: 3, name: "Task 3\u00A0AdditionalInfo", project_id: 1 },
            ],
        },
    },
    views: {
        "account.analytic.line,false,form": `
            <form>
                <field name="project_id"/>
                <field name="task_id"/>
                <field name="unit_amount"/>
            </form>
        `,
        "account.analytic.line,false,list": `
            <tree editable="bottom">
                <field name="project_id"/>
                <field name="task_id"/>
                <field name="unit_amount"/>
            </tree>
        `,
    },
}));

export function updateArch(serverData, fieldNameWidgetNameMapping = {}, fieldNameContextMapping = {}) {
    for (const viewKey in serverData.views) {
        for (const [fieldName, widgetName] of Object.entries(fieldNameWidgetNameMapping)) {
            serverData.views[viewKey] = serverData.views[viewKey].replace(
                `name="${fieldName}"`,
                `name="${fieldName}" widget="${widgetName}"`
            );
        }
        for (const [fieldName, context] of Object.entries(fieldNameContextMapping)) {
            serverData.views[viewKey] = serverData.views[viewKey].replace(
                `name="${fieldName}"`,
                `name="${fieldName}" context="${context}"`
            );
        }
    }
}

export function addFieldsInArch(serverData, fields, beforeField) {
    let fieldsArch = "";
    for (const field of fields) {
        fieldsArch += `<field name="${field}"/>
                `;
    }
    for (const viewKey in serverData.views) {
        serverData.views[viewKey] = serverData.views[viewKey].replace(
            `<field name="${beforeField}"`,
            `${fieldsArch}<field name="${beforeField}"`
        );
    }
}

export function setupTestEnv() {
    setupViewRegistries();

    patchWithCleanup(session, {
        user_companies: {
            current_company: 1,
            allowed_companies: {
                1: {
                    id: 1,
                    name: 'Company',
                    timesheet_uom_id: 1,
                    timesheet_uom_factor: 1,
                },
            },
        },
        user_context: {
            allowed_company_ids: [1],
        },
        uom_ids: {
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
        },
    });

    const serviceRegistry = registry.category("services");
    serviceRegistry.add("company", companyService, { force: true });
}
