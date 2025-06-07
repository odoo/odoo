import { describe, expect, test } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { Component, xml } from "@odoo/owl";
import {
    Country,
    Partner,
    Player,
    Product,
    Stage,
    Team,
} from "@web/../tests/core/tree_editor/condition_tree_editor_test_helpers";
import {
    contains,
    defineModels,
    makeDialogMockEnv,
    mountWithCleanup,
    onRpc,
} from "@web/../tests/web_test_helpers";

import { DomainSelectorDialog } from "@web/core/domain_selector_dialog/domain_selector_dialog";

describe.current.tags("desktop");

async function makeDomainSelectorDialog(params = {}) {
    const props = { ...params };

    class Parent extends Component {
        static components = { DomainSelectorDialog };
        static template = xml`<DomainSelectorDialog t-props="domainSelectorProps"/>`;
        static props = ["*"];
        setup() {
            this.domainSelectorProps = {
                readonly: false,
                domain: "[]",
                close: () => {},
                onConfirm: () => {},
                ...props,
                resModel: "partner",
            };
        }
    }

    const env = await makeDialogMockEnv();
    return mountWithCleanup(Parent, { env, props });
}

defineModels([Partner, Product, Team, Player, Country, Stage]);

test("a domain with a user context dynamic part is valid", async () => {
    await makeDomainSelectorDialog({
        domain: "[('foo', '=', uid)]",
        onConfirm(domain) {
            expect(domain).toBe("[('foo', '=', uid)]");
            expect.step("confirmed");
        },
    });
    onRpc("/web/domain/validate", () => {
        expect.step("validation");
        return true;
    });
    await contains(".o_dialog footer button").click();
    expect.verifySteps(["validation", "confirmed"]);
});

test("can extend eval context", async () => {
    await makeDomainSelectorDialog({
        domain: "['&', ('foo', '=', uid), ('bar', '=', var)]",
        context: { uid: 99, var: "true" },
        onConfirm(domain) {
            expect(domain).toBe("['&', ('foo', '=', uid), ('bar', '=', var)]");
            expect.step("confirmed");
        },
    });
    onRpc("/web/domain/validate", () => {
        expect.step("validation");
        return true;
    });
    await contains(".o_dialog footer button").click();
    expect.verifySteps(["validation", "confirmed"]);
});

test("a domain with an unknown expression is not valid", async () => {
    await makeDomainSelectorDialog({
        domain: "[('foo', '=', unknown)]",
        onConfirm() {
            expect.step("confirmed");
        },
    });
    onRpc("/web/domain/validate", () => {
        expect.step("validation");
        return true;
    });
    await contains(".o_dialog footer button").click();
    expect.verifySteps([]);
});

test("model_field_selector should close on dialog drag", async () => {
    await makeDomainSelectorDialog({
        domain: "[('foo', '=', unknown)]",
    });

    expect(".o_model_field_selector_popover").toHaveCount(0);
    await contains(".o_model_field_selector_value").click();
    expect(".o_model_field_selector_popover").toHaveCount(1);

    const header = queryOne(".modal-header");
    const headerRect = header.getBoundingClientRect();
    await contains(header).dragAndDrop(document.body, {
        position: {
            // the util function sets the source coordinates at (x; y) + (w/2; h/2)
            // so we need to move the dialog based on these coordinates.
            x: headerRect.x + headerRect.width / 2 + 20,
            y: headerRect.y + headerRect.height / 2 + 50,
        },
    });
    await animationFrame();
    expect(".o_model_field_selector_popover").toHaveCount(0);
});
