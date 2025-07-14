import { expect, test } from "@odoo/hoot";
import { click, queryAttribute } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { Component, useState, xml } from "@odoo/owl";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";

import { TagsList } from "@web/core/tags_list/tags_list";

test("Can be rendered with different tags", async () => {
    class Parent extends Component {
        static props = ["*"];
        static components = { TagsList };
        static template = xml`<TagsList tags="tags" />`;
        setup() {
            this.tags = [
                {
                    id: "tag1",
                    text: "Earth",
                },
                {
                    colorIndex: 1,
                    id: "tag2",
                    text: "Wind",
                    onDelete: () => {
                        expect.step(`tag2 delete button has been clicked`);
                    },
                },
                {
                    colorIndex: 2,
                    id: "tag3",
                    text: "Fire",
                    onClick: () => {
                        expect.step(`tag3 has been clicked`);
                    },
                },
            ];
        }
    }

    await mountWithCleanup(Parent);
    expect(".o_tag").toHaveCount(3);

    await click(".o_tag:nth-of-type(2) .o_delete");
    expect.verifySteps(["tag2 delete button has been clicked"]);

    await click(".o_tag:nth-of-type(3)");
    expect.verifySteps(["tag3 has been clicked"]);
});

test("Tags can be displayed with an image", async () => {
    class Parent extends Component {
        static props = ["*"];
        static components = { TagsList };
        static template = xml`<TagsList tags="tags" />`;
        setup() {
            this.tags = [
                {
                    img: "fake/url",
                    id: "tag1",
                    text: "Earth",
                },
                {
                    img: "fake/url/2",
                    id: "tag2",
                    text: "Wind",
                },
            ];
        }
    }

    await mountWithCleanup(Parent);
    expect(".o_tag").toHaveCount(2);
    expect(".o_tag:nth-of-type(1) img").toHaveAttribute("data-src", "fake/url");
    expect(".o_tag:nth-of-type(2) img").toHaveAttribute("data-src", "fake/url/2");
});

test("Tags can be displayed with an icon", async () => {
    class Parent extends Component {
        static props = ["*"];
        static components = { TagsList };
        static template = xml`<TagsList tags="tags" />`;
        setup() {
            this.tags = [
                {
                    icon: "fa-trash",
                    id: "tag1",
                    text: "Bad",
                },
                {
                    icon: "fa-check",
                    id: "tag2",
                    text: "Good",
                },
            ];
        }
    }

    await mountWithCleanup(Parent);
    expect(".o_tag").toHaveCount(2);
    expect(".o_tag:nth-of-type(1) i").toHaveClass("fa fa-trash");
    expect(".o_tag:nth-of-type(2) i").toHaveClass("fa fa-check");
});

test("Limiting the visible tags displays a counter", async () => {
    class Parent extends Component {
        static props = ["*"];
        static components = { TagsList };
        static template = xml`<TagsList tags="tags" visibleItemsLimit="state.visibleItemsLimit" />`;
        setup() {
            this.state = useState({
                visibleItemsLimit: 3,
            });
            this.tags = [
                {
                    id: "tag1",
                    text: "Water",
                    onDelete: () => {},
                },
                {
                    id: "tag2",
                    text: "Grass",
                },
                {
                    id: "tag3",
                    text: "Fire",
                },
                {
                    id: "tag4",
                    text: "Earth",
                },
                {
                    id: "tag5",
                    text: "Wind",
                },
                {
                    id: "tag6",
                    text: "Dust",
                },
            ];
        }
    }

    const parent = await mountWithCleanup(Parent);
    // visibleItemsLimit = 3 -> displays 2 tags + 1 counter (4 tags left)
    expect(".o_tag").toHaveCount(2);
    expect(".rounded").toHaveText("+4", {
        message: "the counter displays 4 more items",
    });
    expect(JSON.parse(queryAttribute(".rounded", "data-tooltip-info"))).toEqual(
        {
            tags: [
                { text: "Fire", id: "tag3" },
                { text: "Earth", id: "tag4" },
                { text: "Wind", id: "tag5" },
                { text: "Dust", id: "tag6" },
            ],
        },
        { message: "the counter has a tooltip displaying other items" }
    );

    parent.state.visibleItemsLimit = 5;
    await animationFrame();
    // visibleItemsLimit = 5 -> displays 4 tags + 1 counter (2 tags left)
    expect(".o_tag").toHaveCount(4);
    expect(".rounded").toHaveText("+2");

    parent.state.visibleItemsLimit = 6;
    await animationFrame();
    // visibleItemsLimit = 6 -> displays 6 tags + 0 counter (0 tag left)
    expect(".o_tag").toHaveCount(6);
    expect(".rounded").toHaveCount(0);
});
