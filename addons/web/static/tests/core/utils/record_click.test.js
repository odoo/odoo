import { expect, test } from "@odoo/hoot";
import { keyDown } from "@odoo/hoot-dom";
import { Component, xml } from "@odoo/owl";
import { contains, mountWithCleanup } from "@web/../tests/web_test_helpers";

import { useRecordClick } from "@web/core/utils/record_click";

test("click behavior on specified element", async () => {
    class MiddleClick extends Component {
        static props = ["*"];
        static template = xml`
            <div class="root">
                <h2>Wonderful Component</h2>
                <button t-ref="recordRef" class="btn btn-primary">Click me!</button>
            </div>
        `;

        setup() {
            useRecordClick({
                onOpen: ({ middleClick }) => {
                    expect.step("middleClick = " + middleClick);
                },
                refName: "recordRef",
            });
        }
    }

    await mountWithCleanup(MiddleClick);

    expect.verifySteps([]);
    await contains(".btn").click();
    expect.verifySteps(["middleClick = false"]);
    await keyDown("Control");
    await contains(".btn").click();
    expect.verifySteps(["middleClick = true"]);
});

test("nested usage of the hook element", async () => {
    class ButtonComponent extends Component {
        static props = ["*"];
        static template = xml`
            <button t-ref="recordRef" class="btn btn-primary">button</button>
        `;
        setup() {
            useRecordClick({
                onOpen: ({ middleClick }) => {
                    expect.step(
                        `record ${this.props.record.id} clicked with middleClick = ${middleClick}`
                    );
                },
                refName: "recordRef",
            });
        }
    }
    class MiddleClick extends Component {
        static props = ["*"];
        static components = { ButtonComponent };
        static template = xml`
            <ul class="root" t-ref="root">
                <li><span>I'm a row and this is a </span><ButtonComponent record="{id: 1}" /></li>
                <li><span>I'm another row and this is another </span><ButtonComponent record="{id: 2}" /></li>
            </ul>
        `;

        setup() {
            useRecordClick({
                onOpen: ({ middleClick }) => {
                    expect.step(`list clicked with middleClick = ${middleClick}`);
                },
                refName: "root",
            });
        }
    }

    await mountWithCleanup(MiddleClick);

    expect.verifySteps([]);
    await contains("li:nth-child(1) .btn").click();
    expect.verifySteps(["record 1 clicked with middleClick = false"]);
    await keyDown("Control");
    await contains("li:nth-child(2) .btn").click();
    expect.verifySteps(["record 2 clicked with middleClick = true"]);
    await keyDown("Control");
    await contains("li:nth-child(2) span").click();
    expect.verifySteps(["list clicked with middleClick = true"]);
});

test("handle global click on element with exceptions", async () => {
    class ButtonComponent extends Component {
        static props = ["*"];
        static template = xml`
            <button t-ref="recordRef" class="btn btn-primary">button</button>
        `;
        setup() {
            useRecordClick({
                onOpen: ({ middleClick }) => {
                    expect.step(`record clicked with middleClick = ${middleClick}`);
                },
                refName: "recordRef",
            });
        }
    }
    class MiddleClick extends Component {
        static props = ["*"];
        static components = { ButtonComponent };
        static template = xml`
            <div class="card h-100" t-ref="root">
                <div class="h-25">
                    <div>We don't want this area to be clickable.</div>
                    <span>But here we have a </span><ButtonComponent />
                </div>
                <div class="h-75">
                    <div>This area is fully clickable to open a record in a new tab</div>
                    <a href="#" t-on-click.prevent.stop="onLinkClick">I'm a link</a>
                </div>
            </div>
        `;

        setup() {
            useRecordClick({
                onOpen: ({ ev, middleClick }) => {
                    if (ev.target.tagName === "A") {
                        expect(ev.target).toHaveText("I look like a link");
                        // we can handle its own logic for the click on this <a> element (e.g. open a record in a new tab)
                        expect.step(`link clicked with middleClick = ${middleClick}`);
                    } else {
                        expect.step(`card clicked with middleClick = ${middleClick}`);
                    }
                },
                refName: "root",
                excludedSelectors: ["div.h-25"],
            });
        }
        onLinkClick() {
            expect.step("link clicked");
        }
    }

    await mountWithCleanup(MiddleClick);

    expect.verifySteps([]);
    await contains(".h-25 .btn").click();
    expect.verifySteps(["record clicked with middleClick = false"]);
    await keyDown("Control");
    await contains(".h-25 div").click();
    expect.verifySteps([]);
    await contains(".h-75 div").click();
    expect.verifySteps(["card clicked with middleClick = true"]);
    await contains(".h-75 a").click();
    expect.verifySteps(["link clicked"]);
});

test("click some lines list", async () => {
    class MiddleClick extends Component {
        static props = ["*"];
        static template = xml`
            <table t-ref="table">
                <tr>
                    <th class="header">Header</th>
                </tr>
                <tr>
                    <td class="selector">Content</td>
                </tr>
            </table>
        `;

        setup() {
            useRecordClick({
                onOpen: () => {
                    expect.step("clicked");
                },
                refName: "table",
                excludedSelectors: [".header"],
            });
        }
    }

    await mountWithCleanup(MiddleClick);

    expect.verifySteps([]);
    await contains(".selector").click();
    expect.verifySteps(["clicked"]);
    await contains(".header").click();
    expect.verifySteps([]);
});

test("hook can be used to target clicks on elements generated by a loop", async () => {
    class MiddleClick extends Component {
        static props = ["*"];
        static template = xml`
            <table t-ref="table">
                <tr>
                    <t t-foreach="records" t-as="r" t-key="r.id">
                        <th class="title" t-att-id="r.id" t-esc="r.title" />
                    </t>
                </tr>
                <tr>
                    <t t-foreach="records" t-as="r" t-key="r.id">
                        <td class="item" t-att-id="r.id" t-esc="r.value" />
                    </t>
                </tr>
            </table>
        `;

        setup() {
            this.records = [
                { id: 1, title: "first", value: "Middle" },
                { id: 2, title: "second", value: "Click" },
            ];
            useRecordClick({
                onOpen: ({ node }) => {
                    expect(node).toHaveClass("item");
                    expect(node).toHaveAttribute("id", "2");
                    expect.step("clicked");
                },
                refName: "table",
                selector: ".item",
            });
        }
    }

    await mountWithCleanup(MiddleClick);

    expect.verifySteps([]);
    await contains(".title:nth-child(2)").click();
    expect.verifySteps([]);
    await contains(".item:nth-child(2)").click();
    expect.verifySteps(["clicked"]);
});
