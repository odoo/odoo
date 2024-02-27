import { expect, test } from "@odoo/hoot";
import { click, queryAttribute } from "@odoo/hoot-dom";
import { Component, xml } from "@odoo/owl";
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

    click(".o_tag:nth-of-type(2) .o_delete");
    expect(["tag2 delete button has been clicked"]).toVerifySteps();

    click(".o_tag:nth-of-type(3)");
    expect(["tag3 has been clicked"]).toVerifySteps();
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
        static template = xml`<TagsList tags="tags" itemsVisible="3" />`;
        setup() {
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

    await mountWithCleanup(Parent);
    expect(".o_tag").toHaveCount(2);
    expect(".rounded-circle", {
        message: "the counter displays 4 more items",
    }).toHaveText("+4");
    expect(JSON.parse(queryAttribute(".rounded-circle", "data-tooltip-info")), {
        message: "the counter has a tooltip displaying other items",
    }).toEqual({
        tags: [
            { text: "Fire", id: "tag3" },
            { text: "Earth", id: "tag4" },
            { text: "Wind", id: "tag5" },
            { text: "Dust", id: "tag6" },
        ],
    });
});

test("Tags with img have a backdrop only if they can be deleted", async () => {
    class Parent extends Component {
        static props = ["*"];
        static components = { TagsList };
        static template = xml`<TagsList tags="tags" />`;
        setup() {
            this.tags = [
                {
                    id: "tag1",
                    text: "Earth",
                    img: "fake/url",
                },
                {
                    colorIndex: 1,
                    id: "tag2",
                    text: "Wind",
                    img: "fake/url",
                    onDelete: () => {},
                },
            ];
        }
    }

    await mountWithCleanup(Parent);
    expect(".o_tag").toHaveCount(2);
    expect(".o_tag:nth-of-type(1) .o_avatar_backdrop").toHaveCount(0);
    expect(".o_tag:nth-of-type(2) .o_avatar_backdrop").toHaveCount(1);
});
