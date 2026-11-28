import { describe, test } from "@odoo/hoot";
import {
    click,
    contains,
    openFormView,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { getService } from "@web/../tests/web_test_helpers";

import { defineProjectModels } from "./project_models";

describe.current.tags("desktop");
defineProjectModels();

test("removing a collaborator from the followers asks for confirmation", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Portal Collaborator" });
    const projectId = pyEnv["project.project"].create({ name: "Shared Project" });
    pyEnv["mail.followers"].create({
        is_active: true,
        partner_id: partnerId,
        res_id: projectId,
        res_model: "project.project",
    });
    await start();
    await openFormView("project.project", projectId, {
        arch: `
            <form>
                <field name="name"/>
                <chatter/>
            </form>`,
    });
    await contains(".o-mail-Followers-counter", { text: "1" });
    getService("mail.store").Thread.insert({
        model: "project.project",
        id: projectId,
        collaborator_ids: [partnerId],
    });
    await click(".o-mail-Followers-button");
    await click(".o-mail-Follower:contains(Portal Collaborator) [title='Remove this follower']");
    await contains(".modal-title", { text: "Remove Collaborator" });
    await click(".modal-footer button", { text: "Discard" });
    await contains(".modal-title", { count: 0 });
    await contains(".o-mail-Followers-counter", { text: "1" });
    await contains(".o-mail-Follower", { text: "Portal Collaborator" });
    await click(".o-mail-Follower:contains(Portal Collaborator) [title='Remove this follower']");
    await click(".modal-footer button", { text: "Remove Collaborator" });
    await contains(".o-mail-Followers-counter", { text: "0" });
});
