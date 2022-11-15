/** @odoo-module **/

import { ActivityMarkAsDone } from "@mail/new/activity/activity_markasdone_popover";
import { click, getFixture, mount, patchWithCleanup } from "@web/../tests/helpers/utils";
import { makeTestEnv, TestServer } from "../helpers/helpers";

let target;

QUnit.module("mail", (hooks) => {
    hooks.beforeEach(async () => {
        target = getFixture();
    });

    QUnit.module("activity_mark_as_done_popover");

    QUnit.test("Activity mark as done popover", async (assert) => {
        const server = new TestServer();
        const env = makeTestEnv((route, params) => {
            if (
                [
                    "/web/dataset/call_kw/mail.activity/action_feedback",
                    "/mail/thread/messages",
                ].includes(route)
            ) {
                assert.step(route);
            }
            return server.rpc(route, params);
        });
        const activity = server.addActivity(1);
        await mount(ActivityMarkAsDone, target, {
            env,
            props: { activity },
        });
        await click(document.querySelector(".o-mail-activity-mark-as-done-button-done"));
        assert.verifySteps([
            "/web/dataset/call_kw/mail.activity/action_feedback",
            "/mail/thread/messages",
        ]);
    });

    QUnit.test("Activity mark as done popover", async (assert) => {
        const server = new TestServer();
        const env = makeTestEnv((route, params) => {
            if (
                [
                    "/web/dataset/call_kw/mail.activity/action_feedback",
                    "/mail/thread/messages",
                ].includes(route)
            ) {
                assert.step(route);
            }
            return server.rpc(route, params);
        });
        patchWithCleanup(env.services.action, {
            doAction(action, options) {
                assert.step("open_activity_form_view");
            },
        });
        const activity = server.addActivity(1);
        await mount(ActivityMarkAsDone, target, {
            env,
            props: { activity },
        });
        await click(
            document.querySelector(".o-mail-activity-mark-as-done-button-done-and-schedule")
        );
        assert.verifySteps([
            "/web/dataset/call_kw/mail.activity/action_feedback",
            "/mail/thread/messages",
            "open_activity_form_view",
        ]);
    });
});
