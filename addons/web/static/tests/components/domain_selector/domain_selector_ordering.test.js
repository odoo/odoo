// @ts-check

import { expect, test } from "@odoo/hoot";
import { queryAllTexts } from "@odoo/hoot-dom";
import { animationFrame, Deferred } from "@odoo/hoot-mock";
import { Component, useState, xml } from "@odoo/owl";
import {
    Country,
    Partner,
    Player,
    Product,
    Stage,
    Team,
} from "@web/../tests/components/tree_editor/condition_tree_editor_test_helpers";
import {
    defineModels,
    getService,
    mountWithCleanup,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { DomainSelector } from "@web/components/domain_selector";

defineModels([Partner, Product, Team, Player, Country, Stage]);

test("two domain updates in flight land in the order they were asked for", async () => {
    /** @type {any[]} */
    const pending = [];
    class Parent extends Component {
        static components = { DomainSelector };
        static template = xml`<DomainSelector resModel="'partner'" domain="this.state.domain" readonly="true" update="() => {}"/>`;
        static props = ["*"];
        /** @type {{ domain: string }} */
        state;
        setup() {
            this.state = useState({ domain: `[("foo", "=", "first")]` });
        }
    }
    /** @type {any} */
    let selector;
    patchWithCleanup(DomainSelector.prototype, {
        setup() {
            selector = this;
            return super.setup();
        },
    });
    const parent = /** @type {any} */ (await mountWithCleanup(Parent));
    expect(queryAllTexts(".o_tree_editor_condition").join(" ")).toInclude("first");

    const treeProcessor = getService("tree_processor");
    patchWithCleanup(treeProcessor, {
        async treeFromDomain(/** @type {any[]} */ ...args) {
            const deferred = new Deferred();
            pending.push({ deferred, args });
            const tree = await super.treeFromDomain(...args);
            await deferred;
            return tree;
        },
    });

    parent.state.domain = `[("foo", "=", "second")]`;
    await animationFrame();
    parent.state.domain = `[("foo", "=", "third")]`;
    await animationFrame();
    expect(pending.length).toBe(2);

    pending[1].deferred.resolve();
    await animationFrame();
    pending[0].deferred.resolve();
    await animationFrame();
    await animationFrame();

    selector.render(true);
    await animationFrame();

    const shown = queryAllTexts(".o_tree_editor_condition").join(" ");
    expect(shown).toInclude("third");
    expect(shown).not.toInclude("second");
});
