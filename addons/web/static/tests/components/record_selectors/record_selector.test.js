// @ts-check

import { expect, test } from "@odoo/hoot";
import { click } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { Component, useState, xml } from "@odoo/owl";
import {
    defineModels,
    fields,
    models,
    mountWithCleanup,
    onRpc,
} from "@web/../tests/web_test_helpers";
import {
    avatarModels,
    isAvatarModel,
} from "@web/components/record_selectors/avatar_models";
import { RecordSelector } from "@web/components/record_selectors/record_selector";

class Partner extends models.Model {
    _name = "res.partner";

    name = fields.Char();

    _records = [
        { id: 1, name: "Alice" },
        { id: 2, name: "Bob" },
        { id: 3, name: "Charlie" },
    ];
}

defineModels([Partner]);

async function mountRecordSelector(/** @type {any} */ props) {
    class Parent extends Component {
        static components = { RecordSelector };
        static template = xml`<RecordSelector t-props="this.recordProps" />`;
        static props = ["*"];
        setup() {
            this.state = useState({ resId: props.resId });
        }

        get recordProps() {
            return {
                ...props,
                resId: this.state.resId,
                update: (/** @type {any} */ resId) => this._update(resId),
            };
        }

        _update(/** @type {any} */ resId) {
            this.state.resId = resId;
        }
    }

    await mountWithCleanup(Parent);
}

test("Can be renderer with no values", async () => {
    await mountRecordSelector({
        resModel: "res.partner",
        resId: false,
    });

    expect(".o_record_selector input").toHaveValue("");
    expect(".o_record_selector input").toHaveClass("o_input");
});

test("Can be renderer with a value", async () => {
    await mountRecordSelector({
        resModel: "res.partner",
        resId: 1,
    });

    expect(".o_record_selector input").toHaveValue("Alice");
});

test("Can be updated from autocomplete", async () => {
    await mountRecordSelector({
        resModel: "res.partner",
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

test("Can display avatars with the right model", async () => {
    await mountRecordSelector({
        resModel: "res.partner",
        resId: 1,
    });

    expect(".o_record_selector input").toHaveValue("Alice");
    expect(".o-autocomplete--dropdown-menu").toHaveCount(0);
    await click(".o_record_selector input");
    await animationFrame();
    expect(".o-autocomplete--dropdown-menu").toHaveCount(1);
    expect(".o-autocomplete--dropdown-menu span.o_avatar img").toHaveCount(3);
    expect(".o-autocomplete--dropdown-menu span.o_avatar img:eq(1)").toHaveAttribute(
        "data-src",
        "https://www.hoot.test/web/image/res.partner/2/avatar_128",
    );
    await click("li.o-autocomplete--dropdown-item:eq(1)");
    await animationFrame();
    expect(".o_record_selector input").toHaveValue("Bob");
    expect(".o_record_selector .o_m2o_avatar").toHaveCount(1);
    expect(".o_record_selector .o_m2o_avatar img").toHaveAttribute(
        "data-src",
        "https://www.hoot.test/web/image/res.partner/2/avatar_128",
    );
});

test("Display name is correctly fetched", async () => {
    expect.assertions(3);
    onRpc("res.partner", "web_search_read", ({ kwargs }) => {
        expect.step("web_search_read");
        expect(kwargs.domain).toEqual([["id", "in", [1]]]);
    });
    await mountRecordSelector({
        resModel: "res.partner",
        resId: 1,
    });

    expect(".o_record_selector input").toHaveValue("Alice");
    expect.verifySteps(["web_search_read"]);
});

test("Can give domain and context props for the name search", async () => {
    expect.assertions(5);
    onRpc("res.partner", "web_name_search", ({ kwargs }) => {
        expect.step("web_name_search");
        expect(kwargs.domain).toEqual([
            "&",
            ["display_name", "=", "Bob"],
            "!",
            ["id", "in", []],
        ]);
        expect(kwargs.context.blip).toBe("blop");
    });
    await mountRecordSelector({
        resModel: "res.partner",
        resId: 1,
        domain: [["display_name", "=", "Bob"]],
        context: { blip: "blop" },
    });

    expect(".o_record_selector input").toHaveValue("Alice");
    expect.verifySteps([]);
    await click(".o_record_selector input");
    await animationFrame();
    expect.verifySteps(["web_name_search"]);
});

test("Support placeholder", async () => {
    await mountRecordSelector({
        resModel: "res.partner",
        resId: false,
        placeholder: "Select a partner",
    });
    expect(".o_record_selector input").toHaveAttribute(
        "placeholder",
        "Select a partner",
    );
});

test("an addon declares its own avatar models through the registry", async () => {
    expect(isAvatarModel("res.partner")).toBe(true);
    expect(isAvatarModel("res.users")).toBe(true);
    expect(isAvatarModel("hr.employee")).toBe(false, {
        message: "web must not name a model it cannot depend on",
    });

    avatarModels.add("hr.employee", true);
    expect(isAvatarModel("hr.employee")).toBe(true);
});

test("the registry, not a literal, decides whether the selector draws an avatar", async () => {
    avatarModels.remove("res.partner");
    await mountRecordSelector({ resModel: "res.partner", resId: 1 });
    expect(".o_record_selector .o_m2o_avatar").toHaveCount(0);

    avatarModels.add("res.partner", true);
    await mountRecordSelector({ resModel: "res.partner", resId: 1 });
    expect(".o_record_selector .o_m2o_avatar").toHaveCount(1);
});
