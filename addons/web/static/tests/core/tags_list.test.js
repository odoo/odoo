import { expect, test } from "@odoo/hoot";
import { click } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { Component, useState, xml } from "@odoo/owl";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { TagsList } from "@web/core/tags_list/tags_list";

test("Limiting the visible tags displays a clickable counter badge", async () => {
    class Parent extends Component {
        static props = ["*"];
        static components = { TagsList };
        static template = xml`
            <TagsList tags="this.tags" tagLimit="this.state.tagLimit" t-slot-scope="tag">
                <span class="custom_tag" t-out="tag.text"/>
            </TagsList>
        `;
        setup() {
            this.state = useState({
                tagLimit: 3,
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
    // tagLimit = 3 -> displays 2 tags + 1 counter (4 tags left)
    expect(".custom_tag").toHaveCount(2);
    expect(".o_badge.bg-secondary").toHaveText("+4", {
        message: "the counter displays 4 more items",
    });
    expect(".o_badge.bg-secondary").toHaveAttribute("data-tooltip", "Click to show more", {
        message: "the counter has the correct static tooltip",
    });

    parent.state.tagLimit = 5;
    await animationFrame();

    // limit = 5 -> displays 4 tags + 1 counter (2 tags left)
    expect(".custom_tag").toHaveCount(4);
    expect(".o_badge.bg-secondary").toHaveText("+2");

    parent.state.tagLimit = 6;
    await animationFrame();
    expect(".custom_tag").toHaveCount(6);
    expect(".o_badge.bg-secondary").toHaveCount(0);

    // Test the click-to-expand behavior
    parent.state.tagLimit = 4;
    await animationFrame();
    expect(".custom_tag").toHaveCount(3);
    // Clicking should override the limit and display ALL tags
    await click(".o_badge.bg-secondary");
    await animationFrame();
    expect(".custom_tag").toHaveCount(6);
    expect(".o_badge.bg-secondary").toHaveCount(0, {
        message: "The counter badge should disappear after expansion",
    });
});
