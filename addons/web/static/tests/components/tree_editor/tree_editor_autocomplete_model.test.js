// @ts-check

import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { Component, useState, xml } from "@odoo/owl";
import {
    defineModels,
    fields,
    models,
    mountWithCleanup,
} from "@web/../tests/web_test_helpers";
import { DomainSelectorAutocomplete } from "@web/components/tree_editor/tree_editor_autocomplete";

class Product extends models.Model {
    _name = "product";
    name = fields.Char();
    _records = [{ id: 37, name: "xphone" }];
}

class ResUsers extends models.Model {
    _name = "res.users";
    name = fields.Char();
    has_group = () => true;
    _records = [{ id: 1, name: "Admin" }];
}

defineModels([Product, ResUsers]);

test("the tag list reads the avatar model from the incoming props, not the outgoing ones", async () => {
    class Parent extends Component {
        static components = { DomainSelectorAutocomplete };
        static template = xml`<DomainSelectorAutocomplete resModel="this.state.resModel" resIds="this.state.resIds" update="() => {}"/>`;
        static props = ["*"];
        /** @type {{ resModel: string, resIds: number[] }} */
        state;
        setup() {
            this.state = useState({ resModel: "res.users", resIds: [1] });
        }
    }

    const parent = /** @type {any} */ (await mountWithCleanup(Parent));
    expect(".o_tag img").toHaveCount(1);

    parent.state.resModel = "product";
    parent.state.resIds = [37];
    await animationFrame();
    await animationFrame();

    expect(".o_tag").toHaveText("xphone");
    expect(".o_tag img").toHaveCount(0);
});
