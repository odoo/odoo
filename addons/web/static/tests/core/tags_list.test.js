import { expect, test } from "@odoo/hoot";
import { queryAttribute } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { Component, useState, xml } from "@odoo/owl";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { TagsList } from "@web/core/tags_list/tags_list";

test("Limiting the visible tags displays a counter", async () => {
    class Parent extends Component {
        static props = ["*"];
        static components = { TagsList };
        static template = xml`
            <TagsList tags="tags" visibleItemsLimit="state.visibleItemsLimit" t-slot-scope="tag">
                <span class="o_tag" t-out="tag.text"/>
            </TagsList>
        `;
        setup() {
            this.state = useState({
                visibleItemsLimit: 3,
            });
            this.tags = [
                { id: "tag1", text: "Water" },
                { id: "tag2", text: "Grass" },
                { id: "tag3", text: "Fire" },
                { id: "tag4", text: "Earth" },
                { id: "tag5", text: "Wind" },
                { id: "tag6", text: "Dust" },
            ];
        }
    }

    const parent = await mountWithCleanup(Parent);
    // visibleItemsLimit = 3 -> displays 2 tags + 1 counter (4 tags left)
    expect(".o_tag").toHaveCount(2);
    expect(".o_tags_list_counter").toHaveText("+4", {
        message: "the counter displays 4 more items",
    });
    expect(JSON.parse(queryAttribute(".o_tags_list_counter", "data-tooltip-info"))).toEqual(
        { tags: ["Fire", "Earth", "Wind", "Dust"] },
        { message: "the counter has a tooltip displaying other items" }
    );

    parent.state.visibleItemsLimit = 5;
    await animationFrame();
    // visibleItemsLimit = 5 -> displays 4 tags + 1 counter (2 tags left)
    expect(".o_tag").toHaveCount(4);
    expect(".o_tags_list_counter").toHaveText("+2");

    parent.state.visibleItemsLimit = 6;
    await animationFrame();
    // visibleItemsLimit = 6 -> displays 6 tags + 0 counter (0 tag left)
    expect(".o_tag").toHaveCount(6);
    expect(".o_tags_list_counter").toHaveCount(0);
});
