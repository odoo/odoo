/** @odoo-module **/

import { Activity } from "@mail/new/chatter/components/activity";
import { makeTestEnv, TestServer } from "@mail/new/helpers/helpers";

import { click, getFixture, mount } from "@web/../tests/helpers/utils";

let target;

QUnit.module("mail", (hooks) => {
    hooks.beforeEach(async () => {
        target = getFixture();
    });

    QUnit.module("activity");

    QUnit.test("Toggle activity detail", async (assert) => {
        const server = new TestServer();
        const env = makeTestEnv((route, params) => server.rpc(route, params));
        const activity = server.addActivity(1);
        await mount(Activity, target, {
            env,
            props: { data: activity },
        });
        await click(document.querySelector(".o-mail-activity-toggle"));
        assert.containsOnce(target, ".o-mail-activity-details", "Activity details should be open.");
        await click(document.querySelector(".o-mail-activity-toggle"));
        assert.containsNone(
            target,
            ".o-mail-activity-details",
            "Activity details should be closed"
        );
    });

    QUnit.test("Delete activity", async (assert) => {
        const server = new TestServer();
        const env = makeTestEnv((route, params) => {
            if (route === "/web/dataset/call_kw/mail.activity/unlink") {
                assert.step("/web/dataset/call_kw/mail.activity/unlink");
            }
            return server.rpc(route, params);
        });
        const activity = server.addActivity(1);
        await mount(Activity, target, {
            env,
            props: { data: activity },
        });
        await click(document.querySelector(".o-mail-activity-unlink-button"));
        assert.verifySteps(["/web/dataset/call_kw/mail.activity/unlink"]);
    });
});
