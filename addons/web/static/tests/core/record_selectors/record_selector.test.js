import { test, expect } from "@odoo/hoot";
import { RecordSelector } from "@web/core/record_selectors/record_selector";
import { Component, useState, xml } from "@odoo/owl";
import {
    defineModels,
    fields,
    models,
    mountWithCleanup,
    onRpc,
} from "@web/../tests/web_test_helpers";
import { animationFrame } from "@odoo/hoot-mock";
import { click } from "@odoo/hoot-dom";

class Partner extends models.Model {
    _name = "partner";

    name = fields.Char();

    _records = [
        { id: 1, name: "Alice" },
        { id: 2, name: "Bob" },
        { id: 3, name: "Charlie" },
    ];
}

defineModels([Partner]);

async function mountRecordSelector(props) {
    class Parent extends Component {
        static components = { RecordSelector };
        static template = xml`<RecordSelector t-props="recordProps" />`;
        static props = ["*"];
        setup() {
            this.state = useState({ resId: props.resId });
        }

        get recordProps() {
            return {
                ...props,
                resId: this.state.resId,
                update: (resId) => this._update(resId),
            };
        }

        _update(resId) {
            this.state.resId = resId;
        }
    }

    await mountWithCleanup(Parent);
}

test("Can be renderer with no values", async () => {
    await mountRecordSelector({
        resModel: "partner",
        resId: false,
    });

    expect(".o_record_selector input").toHaveValue("");
    expect(".o_record_selector input").toHaveClass("o_input");
});

test("Can be renderer with a value", async () => {
    await mountRecordSelector({
        resModel: "partner",
        resId: 1,
    });

    expect(".o_record_selector input").toHaveValue("Alice");
});

test("Can be updated from autocomplete", async () => {
    await mountRecordSelector({
        resModel: "partner",
        resId: 1,
    });

    expect(".o_record_selector input").toHaveValue("Alice");
    expect(".o-autocomplete--dropdown-menu").toHaveCount(0);
    await click(".o_record_selector input");
    await animationFrame();
    expect(".o-autocomplete--dropdown-menu").toHaveCount(1);
    await click("li.o-autocomplete--dropdown-item:eq(1)");
    await animationFrame();
    expect(".o_record_selector input").toHaveValue("Bob");
});

test("Display name is correctly fetched", async () => {
    expect.assertions(3);
    onRpc("partner", "web_search_read", ({ kwargs }) => {
        expect.step("web_search_read");
        expect(kwargs.domain).toEqual([["id", "in", [1]]]);
    });
    await mountRecordSelector({
        resModel: "partner",
        resId: 1,
    });

    expect(".o_record_selector input").toHaveValue("Alice");
    expect.verifySteps(["web_search_read"]);
});

test("Can give domain and context props for the name search", async () => {
    expect.assertions(5);
    onRpc("partner", "name_search", ({ kwargs }) => {
        expect.step("name_search");
        expect(kwargs.args).toEqual(["&", ["display_name", "=", "Bob"], "!", ["id", "in", []]]);
        expect(kwargs.context.blip).toBe("blop");
    });
    await mountRecordSelector({
        resModel: "partner",
        resId: 1,
        domain: [["display_name", "=", "Bob"]],
        context: { blip: "blop" },
    });

    expect(".o_record_selector input").toHaveValue("Alice");
    expect.verifySteps([]);
    await click(".o_record_selector input");
    await animationFrame();
    expect.verifySteps(["name_search"]);
});

test("Support placeholder", async () => {
    await mountRecordSelector({
        resModel: "partner",
        resId: false,
        placeholder: "Select a partner",
    });
    expect(".o_record_selector input").toHaveAttribute("placeholder", "Select a partner");
});
