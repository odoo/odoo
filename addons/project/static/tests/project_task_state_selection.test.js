import { describe, expect, test } from "@odoo/hoot";
import { contains, mountView } from "@web/../tests/web_test_helpers";
import { defineProjectModels } from "@project/../tests/project_test_helpers";
import { startServer } from "@mail/../tests/mail_test_helpers";

describe.current.tags("desktop");
defineProjectModels();

test("project form view", async () => {
    const pyEnv = await startServer();

    const [projectId] = pyEnv['project.project'].create([
        { name: "Project One" },
    ]);
    const userId = pyEnv['res.users'].create([
        { name: "User One", login: 'one', password: 'one' },
    ]);
    pyEnv['project.task'].create([
        { name: 'task one', project_id: projectId, state: '01_in_progress', user_ids: userId, priority: "0" },
        { name: 'task two', state: '03_approved', priority: "0" },
        { name: 'task three', state: '04_waiting_normal', priority: "0" },
    ]);

    await mountView({
        resModel: "project.task",
        type: "kanban",
        arch: `<kanban js_class="project_task_kanban">
                   <templates>
                       <t t-name="kanban-box">
                           <div>
                               <field name="state" widget="project_task_state_selection" class="project_task_state_test"/>
                           </div>
                       </t>
                   </templates>
               </kanban>`,
    });

    expect(".o-dropdown--menu").not.toBeDisplayed();
    await contains("div[name='state']:first-child button.dropdown-toggle").click();
    expect(".o-dropdown--menu").toBeDisplayed();

    await contains(".o-dropdown--menu span.text-danger").click();
    expect("div[name='state']:first-child button.dropdown-toggle i.fa-times-circle").toBeDisplayed();

    await contains("div[name='state'] i.fa-hourglass-o").click();
    expect(".o-dropdown--menu").not.toBeDisplayed();
});
