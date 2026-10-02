import { defineMailModels, start } from "@mail/../tests/mail_test_helpers";
import { Action } from "@mail/core/common/action";
import { ActionList } from "@mail/core/common/action_list";

import { describe, expect, test } from "@odoo/hoot";
import { Component, signal, xml } from "@odoo/owl";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { useService } from "@web/core/utils/hooks";

describe.current.tags("desktop");
defineMailModels();

test("store is correctly set on actions", async () => {
    const storeSym = Symbol("STORE");
    const ownerSym = Symbol("COMPONENT");
    const action = new Action({
        owner: ownerSym,
        id: "test",
        definition: {},
        store: storeSym,
    });
    expect(action.store).toBe(storeSym);
});

test("actions available offline are tagged in default inline and dropdown actions", async () => {
    await start();
    class Parent extends Component {
        static components = { ActionList };
        static template = xml`
            <div class="o-inline-list"><ActionList actions="this.actions" inline="true"/></div>
            <div class="o-dropdown-list"><ActionList actions="this.actions" dropdown="true"/></div>
        `;

        setup() {
            const store = useService("mail.store");
            this.actions = signal([
                new Action({
                    owner: this,
                    id: "offline",
                    definition: { availableOffline: true, icon: "close", name: "Offline" },
                    store,
                }),
                new Action({
                    owner: this,
                    id: "online",
                    definition: { icon: "edit", name: "Online" },
                    store,
                }),
            ]);
        }
    }
    await mountWithCleanup(Parent);
    for (const list of [".o-inline-list", ".o-dropdown-list"]) {
        expect(`${list} button[name='offline']`).toHaveAttribute("data-available-offline");
        expect(`${list} button[name='online']`).not.toHaveAttribute("data-available-offline");
    }
});
