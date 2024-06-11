/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { TagsList } from "@web/core/tags_list/tags_list";
import { makeTestEnv } from "../helpers/mock_env";
import { getFixture, patchWithCleanup, mount, click } from "../helpers/utils";

import { Component, xml } from "@odoo/owl";

QUnit.module("Web Components", (hooks) => {
    QUnit.module("TagsList");

    let env;
    let target;

    hooks.beforeEach(async () => {
        env = await makeTestEnv();
        target = getFixture();
        patchWithCleanup(browser, {
            setTimeout: (fn) => Promise.resolve().then(fn),
        });
    });

    QUnit.test("Can be rendered with different tags", async (assert) => {
        class Parent extends Component {
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
                            assert.step(`tag2 delete button has been clicked`);
                        },
                    },
                    {
                        colorIndex: 2,
                        id: "tag3",
                        text: "Fire",
                        onClick: () => {
                            assert.step(`tag3 has been clicked`);
                        },
                        onDelete: () => {
                            assert.step(`tag3 delete button has been clicked`);
                        },
                    },
                ];
            }
        }
        Parent.components = { TagsList };
        Parent.template = xml`
        <TagsList tags="tags" />`;

        await mount(Parent, target, { env });
        assert.containsN(target, ".o_tag", 3);

        await click(target.querySelector(".o_tag:nth-of-type(2) .o_delete"));
        assert.verifySteps(["tag2 delete button has been clicked"]);

        await click(target.querySelector(".o_tag:nth-of-type(3)"));
        assert.verifySteps(["tag3 has been clicked"]);
    });

    QUnit.test("Tags can be displayed with an image", async (assert) => {
        class Parent extends Component {
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
        Parent.components = { TagsList };
        Parent.template = xml`
        <TagsList tags="tags" />`;

        await mount(Parent, target, { env });
        assert.containsN(target, ".o_tag", 2);
        assert.strictEqual(
            target.querySelector(".o_tag:nth-of-type(1) img").dataset.src,
            "fake/url"
        );
        assert.strictEqual(
            target.querySelector(".o_tag:nth-of-type(2) img").dataset.src,
            "fake/url/2"
        );
    });

    QUnit.test("Tags can be displayed with an icon", async (assert) => {
        class Parent extends Component {
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
        Parent.components = { TagsList };
        Parent.template = xml`
        <TagsList tags="tags" />`;

        await mount(Parent, target, { env });
        assert.containsN(target, ".o_tag", 2);
        assert.hasClass(target.querySelector(".o_tag:nth-of-type(1) i"), "fa fa-trash");
        assert.hasClass(target.querySelector(".o_tag:nth-of-type(2) i"), "fa fa-check");
    });

    QUnit.test("Limiting the visible tags displays a counter", async (assert) => {
        class Parent extends Component {
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
        Parent.components = { TagsList };
        Parent.template = xml`
        <TagsList tags="tags" itemsVisible="3" />`;

        await mount(Parent, target, { env });
        assert.containsN(target, ".o_tag", 2);

        const counter = target.querySelector(".rounded-circle");
        assert.strictEqual(counter.textContent, "+4", "the counter displays 4 more items");
        assert.deepEqual(
            JSON.parse(counter.dataset.tooltipInfo),
            {
                tags: [
                    { text: "Fire", id: "tag3" },
                    { text: "Earth", id: "tag4" },
                    { text: "Wind", id: "tag5" },
                    { text: "Dust", id: "tag6" },
                ],
            },
            "the counter has a tooltip displaying other items"
        );
    });

    QUnit.test("Tags with img have a backdrop only if they can be deleted", async (assert) => {
        class Parent extends Component {
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
        Parent.components = { TagsList };
        Parent.template = xml`<TagsList tags="tags" />`;

        await mount(Parent, target, { env });
        assert.containsN(target, ".o_tag", 2);
        assert.containsNone(target.querySelectorAll(".o_tag")[0], ".o_avatar_backdrop");
        assert.containsOnce(target.querySelectorAll(".o_tag")[1], ".o_avatar_backdrop");
    });
});
