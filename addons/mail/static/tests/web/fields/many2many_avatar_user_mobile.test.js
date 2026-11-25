import { defineMailModels, openFormView, start, startServer } from "@mail/../tests/mail_test_helpers";
import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { contains, onRpc } from "@web/../tests/web_test_helpers";
import { ResUsers } from "../../mock_server/mock_models/res_users";

defineMailModels();
describe.current.tags("mobile");

beforeEach(() => {
    ResUsers._views.kanban = /* xml */ `
        <kanban>
            <templates>
                <t t-name="card">
                    <field name="name"/>
                </t>
            </templates>
        </kanban>
    `;
});

test("avatar user fields ask for the current user first in the select dialog", async () => {
    const pyEnv = await startServer();
    const avatarUserId = pyEnv["m2x.avatar.user"].create({});
    onRpc("res.users", "web_search_read", ({ kwargs }) => {
        expect.step(`current_user_first: ${kwargs.context.current_user_first}`);
    });
    await start();
    await openFormView("m2x.avatar.user", avatarUserId, {
        arch: `
            <form>
                <field name="user_id" widget="many2one_avatar_user"/>
                <field name="user_ids" widget="many2many_avatar_user"/>
            </form>`,
    });
    await contains(".o_field_many2one_avatar_user input").click();
    await contains(".o_dialog .modal-footer button:contains(Close)").click();
    await contains(".o_field_many2many_avatar_user input").click();
    await expect.waitForSteps(["current_user_first: true", "current_user_first: true"]);
});
