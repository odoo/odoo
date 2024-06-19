import { expect, test,beforeEach, describe } from "@odoo/hoot";
import { click,} from "@mail/../tests/mail_test_helpers";
import { mountView, onRpc, contains, webModels } from "@web/../tests/web_test_helpers";
import { ProjectTask } from "./project_models";
import { defineProjectModels, ProjectProject } from "@project/../tests/project_models";

defineProjectModels();
describe.current.tags("desktop");

beforeEach(() => {
    webModels.ResUsers._records = [
        { id: 1, name: "User1" },
        ...webModels.ResUsers._records,
    ];
    ProjectProject._records = [
        { id: 1, name: "service", planned_date_begin: "2019-03-12 06:30:00",},
    ];
    ProjectTask._records = [
        {
            name: "Task 1",
            planned_date_begin: "2019-03-12 06:30:00",
            date_deadline: "2019-03-12 12:30:00",
            project_id: 1,
            user_ids: [1],
        },
    ];
});

onRpc(async ({ method }) => {
    if (method === "check_access_rights") {
        return true;
    } else if(method === "get_formview_id") {
        return true;
    }
});

test("fa-expand button test for task form view ", async () => {
    ProjectTask._views.form = `
    <form>
        <field name="name"/>
        <footer>
            <button string="Save &amp; Close" special="save" data-hotkey="q" class="btn btn-primary" close="1"/>
            <button string="Discard" special="cancel" data-hotkey="x" class="btn btn-secondary" close="1"/>
            <button name="action_open_task" type="object" title="View task" class="btn btn-secondary w-md-auto ms-auto" close="1">
                <i class="fa fa-expand"/>
            </button>
        </footer>
    </form>`;

    onRpc(async ({ method }) => {
        if(method === "action_open_task") {
            expect.step(method)
            return true;
        }
    });

    await mountView({
        type:'calendar',
        resModel:'project.task',
        arch: `<calendar date_start="planned_date_begin" event_open_popup="1" js_class="project_task_calendar" mode="month"/>`,
    });

    expect(".o_event_title").toHaveCount(1);
    await click(".o_event_title");

    await click(".o_cw_popover_edit");
    await contains("button[name='action_open_task']").click();
    expect(['action_open_task']).toVerifySteps();
});

test("fa-expand button test for project form view ", async () => {
    ProjectProject._views.form = `
    <form>
        <field name="name"/>
        <footer>
            <button string="Save &amp; Close" special="save" data-hotkey="q" class="btn btn-primary" close="1"/>
            <button string="Discard" special="cancel" data-hotkey="x" class="btn btn-secondary" close="1"/>
            <button name="action_view_project" type="object" title="View Project" class="btn btn-secondary w-md-auto ms-auto" close="1">
                <i class="fa fa-expand"/>
            </button>
        </footer>
    </form>`;

    onRpc(async ({ method }) => {
        if(method === "action_view_project") {
            expect.step(method)
            return true;
        }
    });

    await mountView({
        type:'calendar',
        resModel:'project.project',
        arch: `<calendar date_start="planned_date_begin" event_open_popup="true" js_class="project_project_calendar" mode="month"/>`,
    });

    expect(".o_event_title").toHaveCount(1);
    await click(".o_event_title");

    await click(".o_cw_popover_edit");
    await contains("button[name='action_view_project']").click();
    expect(['action_view_project']).toVerifySteps();
});
