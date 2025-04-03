import { test, expect } from "@odoo/hoot";
import { MultiRecordSelector } from "@web/core/record_selectors/multi_record_selector";
import { Component, useState, xml } from "@odoo/owl";
import {
    contains,
    defineModels,
    fields,
    models,
    mountWithCleanup,
    onRpc,
} from "@web/../tests/web_test_helpers";
import { click, fill, press, queryAllTexts } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";

class Partner extends models.Model {
    _name = "partner";

    name = fields.Char();

    _records = [
        { id: 1, name: "Alice" },
        { id: 2, name: "Bob" },
        { id: 3, name: "Charlie" },
    ];
}

// Required for the select create dialog
class Users extends models.Model {
    _name = "res.users";
    has_group = () => true;
}

defineModels([Partner, Users]);

async function mountMultiRecordSelector(props) {
    class Parent extends Component {
        static components = { MultiRecordSelector };
        static template = xml`<MultiRecordSelector t-props="recordProps" />`;
        static props = ["*"];
        setup() {
            this.state = useState({ resIds: props.resIds });
        }

        get recordProps() {
            return {
                ...props,
                resIds: this.state.resIds,
                update: (resIds) => this._update(resIds),
            };
        }

        _update(resIds) {
            this.state.resIds = resIds;
        }
    }

    await mountWithCleanup(Parent);
}

test("Can be renderer with no values", async () => {
    await mountMultiRecordSelector({
        resModel: "partner",
        resIds: [],
    });

    expect(".o_multi_record_selector input").toHaveValue("");
    expect(".o_multi_record_selector input").toHaveClass("o_input");
});

test("Can be renderer with a value", async () => {
    await mountMultiRecordSelector({
        resModel: "partner",
        resIds: [1],
    });

    expect(".o_multi_record_selector input").toHaveValue("");
    expect(".o_tag").toHaveCount(1);
    expect(".o_tag").toHaveText("Alice");
});

test("Can be renderer with multiple values", async () => {
    await mountMultiRecordSelector({
        resModel: "partner",
        resIds: [1, 2],
    });

    expect(".o_multi_record_selector input").toHaveValue("");
    expect(".o_tag").toHaveCount(2);
    expect(queryAllTexts(".o_tag")).toEqual(["Alice", "Bob"]);
});

test("Can be updated from autocomplete", async () => {
    await mountMultiRecordSelector({
        resModel: "partner",
        resIds: [],
    });

    expect(".o_multi_record_selector input").toHaveValue("");
    expect(".o_tag").toHaveCount(0);
    expect(".o-autocomplete--dropdown-menu").toHaveCount(0);
    await click(".o_multi_record_selector input");
    await animationFrame();
    expect(".o-autocomplete--dropdown-menu").toHaveCount(1);
    await click("li.o-autocomplete--dropdown-item:eq(1)");
    await animationFrame();
    expect(".o_tag").toHaveCount(1);
    expect(".o_tag").toHaveText("Bob");
});

test("Can display avatars with the right model", async () => {
    Partner._name = "res.partner";
    await mountMultiRecordSelector({
        resModel: "res.partner",
        resIds: [],
    });

    expect(".o_multi_record_selector input").toHaveValue("");
    expect(".o_tag").toHaveCount(0);
    expect(".o-autocomplete--dropdown-menu").toHaveCount(0);
    await click(".o_multi_record_selector input");
    await animationFrame();
    expect(".o-autocomplete--dropdown-menu").toHaveCount(1);
    expect("span.o_avatar img").toHaveCount(3);
    expect("span.o_avatar img:eq(1)").toHaveAttribute(
        "data-src",
        "/web/image/res.partner/2/avatar_128"
    );
    await click("li.o-autocomplete--dropdown-item:eq(1)");
    await animationFrame();
    expect(".o_tag").toHaveCount(1);
    expect(".o_tag").toHaveText("Bob");
    expect(".o_tag img.o_m2m_avatar").toHaveCount(1);
    expect(".o_tag img.o_m2m_avatar").toHaveAttribute(
        "data-src",
        "https://www.hoot.test/web/image/res.partner/2/avatar_128"
    );
});

test("Display name is correctly fetched", async () => {
    expect.assertions(4);
    onRpc("partner", "web_search_read", ({ kwargs }) => {
        expect.step("web_search_read");
        expect(kwargs.domain).toEqual([["id", "in", [1]]]);
    });

    await mountMultiRecordSelector({
        resModel: "partner",
        resIds: [1],
    });

    expect(".o_tag").toHaveCount(1);
    expect(".o_tag").toHaveText("Alice");
    expect.verifySteps(["web_search_read"]);
});

test("Can give domain and context props for the name search", async () => {
    expect.assertions(4);
    onRpc("partner", "name_search", ({ kwargs }) => {
        expect.step("name_search");
        expect(kwargs.domain).toEqual(["&", ["display_name", "=", "Bob"], "!", ["id", "in", [1]]]);
        expect(kwargs.context.blip).toBe("blop");
    });

    await mountMultiRecordSelector({
        resModel: "partner",
        resIds: [1],
        domain: [["display_name", "=", "Bob"]],
        context: { blip: "blop" },
    });

    expect.verifySteps([]);
    await click(".o_multi_record_selector input");
    await animationFrame();
    expect.verifySteps(["name_search"]);
});

test("Support placeholder", async () => {
    await mountMultiRecordSelector({
        resModel: "partner",
        resIds: [],
        placeholder: "Select a partner",
    });
    expect(".o_multi_record_selector input").toHaveAttribute("placeholder", "Select a partner");
    await click(".o_multi_record_selector input");
    await animationFrame();
    await contains("li.o-autocomplete--dropdown-item:eq(0)").click();
    expect(".o_multi_record_selector input").toHaveAttribute("placeholder", "");
});

test("Placeholder is not set if values are selected", async () => {
    await mountMultiRecordSelector({
        resModel: "partner",
        resIds: [1],
        placeholder: "Select a partner",
    });
    expect(".o_multi_record_selector input").toHaveAttribute("placeholder", "");
});

test("Can delete a tag with Backspace", async () => {
    await mountMultiRecordSelector({
        resModel: "partner",
        resIds: [1, 2],
    });
    await click(".o_multi_record_selector input");
    await animationFrame();
    await press("Backspace");
    await animationFrame();
    expect(".o_tag").toHaveCount(1);
    expect(".o_tag").toHaveText("Alice");
});

test("Can focus tags with arrow right and left", async () => {
    await mountMultiRecordSelector({
        resModel: "partner",
        resIds: [1, 2],
    });
    // Click twice because to get the focus and make disappear the autocomplete popover
    await click(".o_multi_record_selector input");
    await click(".o_multi_record_selector input");
    await animationFrame();
    await press("arrowleft");
    await animationFrame();
    expect(document.activeElement).toHaveText("Bob");
    await press("arrowleft");
    await animationFrame();
    expect(document.activeElement).toHaveText("Alice");
    await press("arrowleft");
    await animationFrame();
    expect(document.activeElement).toHaveClass("o-autocomplete--input");
    await press("arrowright");
    await animationFrame();
    expect(document.activeElement).toHaveText("Alice");
    await press("arrowright");
    await animationFrame();
    expect(document.activeElement).toHaveText("Bob");
    await press("arrowright");
    await animationFrame();
    expect(document.activeElement).toHaveClass("o-autocomplete--input");
});

test("Delete the focused element", async () => {
    await mountMultiRecordSelector({
        resModel: "partner",
        resIds: [1, 2],
    });
    // Click twice because to get the focus and make disappear the autocomplete popover
    await click(".o_multi_record_selector input");
    await click(".o_multi_record_selector input");
    await animationFrame();

    await press("arrowright");
    await animationFrame();
    expect(document.activeElement).toHaveText("Alice");

    await press("Backspace");
    await animationFrame();
    expect(".o_tag").toHaveCount(1);
    expect(".o_tag").toHaveText("Bob");
});

test("Backspace do nothing when the input is currently edited", async () => {
    await mountMultiRecordSelector({
        resModel: "partner",
        resIds: [1, 2],
    });
    await click(".o-autocomplete input");
    await animationFrame();

    await fill("a");
    await animationFrame();
    expect(document.activeElement).toHaveValue("a");

    await press("Backspace");
    await animationFrame();
    expect(".o_tag").toHaveCount(2);
});

// Desktop only because a kanban view is used instead of a list in mobile
test.tags("desktop");
test("Can pass domain to search more", async () => {
    Partner._records.push(
        { id: 4, name: "David" },
        { id: 5, name: "Eve" },
        { id: 6, name: "Frank" },
        { id: 7, name: "Grace" },
        { id: 8, name: "Helen" },
        { id: 9, name: "Ivy" }
    );
    Partner._views["list"] = /* xml */ `<list><field name="name"/></list>`;
    await mountMultiRecordSelector({
        resModel: "partner",
        resIds: [],
        domain: [["id", "not in", [1]]],
    });
    await click(".o-autocomplete input");
    await animationFrame();

    await click(".o_multi_record_selector .o_m2o_dropdown_option");
    await animationFrame();

    expect(".o_data_row").toHaveCount(8, { message: "should contain 8 records" });
});
