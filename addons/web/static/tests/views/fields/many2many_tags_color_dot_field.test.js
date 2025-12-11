import { expect, test } from "@odoo/hoot";
import { queryAllTexts } from "@odoo/hoot-dom";

import {
    clickFieldDropdown,
    clickFieldDropdownItem,
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
    foo = fields.Char({ default: "My little Foo Value" });
    timmy = fields.Many2many({ relation: "partner.type", string: "pokemon" });

    _views = {
        search: "<search/>",
    };
}

class PartnerType extends models.Model {
    name = fields.Char();
    color = fields.Char({ string: "Color hex" });

    _records = [
        { id: 12, name: "red", color: "#F54927" },
        { id: 14, name: "blue", color: "#603CE2" },
        { id: 31, name: "green", color: "#38E55E" },
        { id: 17, name: "orange", color: "#DE6F3F" },
        { id: 78, name: "purple", color: "#A33AE4" },
        { id: 178, name: "pink", color: "#E43AD0" },
    ];
    _views = {
        search: "<search/>",
        form: `
            <form>
                <group>
                    <field name="name"/>
                    <field name="color" widget="color"/>
                </group>
            </form>`,
    };
}

defineModels([Partner, PartnerType]);

onRpc("get_formview_id", () => true);
onRpc("has_group", () => true);

test.tags("desktop");
test("Many2ManyTagsColorDotField on desktop, can open form on click tag", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="timmy" widget="many2many_tags_color_dot" options="{'color_field': 'color', 'can_open':True}"/>
            </form>`,
    });

    expect("[name=timmy] .o_tag").toHaveCount(0);
    await clickFieldDropdown("timmy");
    expect("[name=timmy] .o-autocomplete.dropdown li").toHaveCount(7, {
        message: "autocomplete dropdown should have 7 entries (6 values + 'Search more...')",
    });
    await clickFieldDropdownItem("timmy", "blue");
    expect("[name=timmy] .o_tag").toHaveCount(1);
    expect(queryAllTexts(`.o_field_many2many_tags[name=timmy] .badge`)).toEqual(["blue"]);
    expect(`[name=timmy] .o_tag_badge_text i`).toHaveStyle("color:rgb(96, 60, 226);");

    expect(".o_dialog").toHaveCount(0);
    await contains("[name=timmy] .o_tag").click();
    expect(".o_dialog").toHaveCount(1);
    await contains(".o_dialog .o_field_color input", { visible: false }).edit("#3ee5d1");
    await contains(".o_dialog button:contains(save)").click();
    expect(`[name=timmy] .o_tag_badge_text i`).toHaveStyle("color:rgb(62, 229, 209);");
});

test.tags("desktop");
test("Many2ManyTagsColorDotField on desktop, cannot open form on click tag", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="timmy" widget="many2many_tags_color_dot" options="{'color_field': 'color'}"/>
            </form>`,
    });

    expect("[name=timmy] .o_tag").toHaveCount(0);
    await clickFieldDropdown("timmy");
    await clickFieldDropdownItem("timmy", "blue");

    expect(".o_dialog").toHaveCount(0);
    await contains("[name=timmy] .o_tag").click();
    expect(".o_dialog").toHaveCount(0);
});
