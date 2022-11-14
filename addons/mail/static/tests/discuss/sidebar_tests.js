/** @odoo-module **/

import { Sidebar } from "@mail/discuss/sidebar";
import { click, getFixture, mount, patchWithCleanup } from "@web/../tests/helpers/utils";
import { browser } from "@web/core/browser/browser";
import { makeMessagingEnv, MessagingServer } from "../helpers/helpers";

let target;

QUnit.module("mail", (hooks) => {
    hooks.beforeEach(async () => {
        target = getFixture();
        // for autocomplete stuff
        patchWithCleanup(browser, {
            setTimeout: (fn) => fn(),
        });
    });

    QUnit.module("discuss sidebar");

    QUnit.test("toggling category button hide category items", async (assert) => {
        const server = new MessagingServer();
        server.addChannel(43, "abc");
        const env = makeMessagingEnv((route, params) => server.rpc(route, params));
        await mount(Sidebar, target, { env });

        assert.containsOnce(target, "button.o-active:contains('Inbox')");
        assert.containsN(target, ".o-mail-category-item", 1);
        await click(target.querySelector(".o-mail-category-icon"));
        assert.containsNone(target, ".o-mail-category-item");
    });

    QUnit.test("toggling category button does not hide active category items", async (assert) => {
        const server = new MessagingServer();
        server.addChannel(43, "abc");
        server.addChannel(46, "def");
        const env = makeMessagingEnv((route, params) => server.rpc(route, params));
        env.services["mail.messaging"].discuss.threadId = 43; // #abc is active

        await mount(Sidebar, target, { env });
        assert.containsN(target, ".o-mail-category-item", 2);
        assert.containsOnce(target, ".o-mail-category-item.o-active");
        await click(target.querySelector(".o-mail-category-icon"));
        assert.containsOnce(target, ".o-mail-category-item");
        assert.containsOnce(target, ".o-mail-category-item.o-active");
    });
});
