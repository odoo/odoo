import { expect, test } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";

import {
    contains,
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
} from "@web/../tests/web_test_helpers";

class Partner extends models.Model {
    _name = "partner";

    name = fields.Char();
    timmy = fields.Many2many({ relation: "partner.type", string: "pokemon" });

    _records = [{ id: 1, name: "first record", timmy: [12, 14] }];
}

class PartnerType extends models.Model {
    name = fields.Char();
    color = fields.Char({ string: "Color hex" });

    _records = [
        { id: 12, name: "red", color: "#F54927" },
        { id: 14, name: "no color", color: false },
    ];
}

defineModels([Partner, PartnerType]);

test("Many2ManyTagsHexColorField: tags take the tones of their color", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <field name="timmy" widget="many2many_tags_hex_color" options="{'color_field': 'color'}"/>
            </form>`,
    });

    expect(".o_field_many2many_tags .o_tag").toHaveCount(2);
    expect(".o_tag:eq(0)").toHaveClass("o_tag_hex_color");
    expect(".o_tag:eq(0)").toHaveAttribute("data-color", "#F54927");
    expect(".o_tag:eq(1)").toHaveClass("o_tag_color_0");
    expect(".o_tag:eq(1)").not.toHaveClass("o_tag_hex_color");
});

test("Many2ManyTagsHexColorField: update color", async () => {
    onRpc("partner.type", "web_save", ({ args }) => {
        expect.step(args[1]);
    });

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <field name="timmy" widget="many2many_tags_hex_color" options="{'color_field': 'color', 'on_tag_click': 'edit_color'}"/>
            </form>`,
    });

    const badgeNode = queryOne(".o_tag:eq(0)");
    await contains(badgeNode).click();
    expect(".o_colorlist").toHaveCount(1);
    expect(".o_colorlist button.o_colorlist_color_0").toHaveCount(0);
    expect(".o_colorlist button.active").toHaveCount(0);
    await contains(".o_colorlist button.o_colorlist_color_8").click();
    expect(".o_colorlist").toHaveCount(0);
    expect(badgeNode).toHaveAttribute("data-color", "#304be0");

    await contains(badgeNode).click();
    expect(".o_colorlist button.o_colorlist_color_8").toHaveClass("active");
    await contains(".o_tag_custom_color", { visible: false }).edit("#3ee5d1");
    expect(badgeNode).toHaveAttribute("data-color", "#3ee5d1");

    expect.verifySteps([{ color: "#304be0" }, { color: "#3ee5d1" }]);
});

test("Many2ManyTagsHexColorField: no color edition without on_tag_click", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <field name="timmy" widget="many2many_tags_hex_color" options="{'color_field': 'color'}"/>
            </form>`,
    });

    await contains(".o_tag:eq(0)").click();
    expect(".o_colorlist").toHaveCount(0);
});
