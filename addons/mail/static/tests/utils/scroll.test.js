import { contains, defineMailModels } from "@mail/../tests/mail_test_helpers";
import { useScrollManager } from "@mail/utils/common/scroll";

import { describe, expect, test } from "@odoo/hoot";
import { Component, onMounted, signal, xml } from "@odoo/owl";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("list resized right after the scroll is applied on mount stays at the end", async () => {
    class List extends Component {
        static template = xml`
            <div class="o-list overflow-auto" style="height: 200px" t-ref="this.listRef">
                <div t-foreach="this.items" t-as="item" t-key="item" style="height: 50px" t-out="item"/>
            </div>
        `;

        setup() {
            this.items = Array.from({ length: 20 }, (_, i) => i);
            this.listRef = signal.ref();
            this.position = "bottom";
            useScrollManager({
                ref: this.listRef,
                ready: () => true,
                bounds: () => ({ start: 0, end: 19 }),
                getPosition: () => this.position,
                setPosition: (position) => (this.position = position),
                getItemEl: () => undefined,
                onNotReady: () => {},
            });
            // after the scroll is applied, before the first frame
            onMounted(() => (this.listRef().style.height = "180px"));
        }
    }
    await mountWithCleanup(List);
    await contains(".o-list", { scroll: "bottom" });
});

test("smooth scroll to the position the list is already at ends at once", async () => {
    class List extends Component {
        static template = xml`
            <div class="o-list overflow-auto" style="height: 200px" t-ref="this.listRef">
                <div t-foreach="this.items" t-as="item" t-key="item" style="height: 50px" t-out="item"/>
            </div>
        `;

        setup() {
            this.items = [0, 1];
            this.listRef = signal.ref();
            this.position = "bottom-smooth";
            useScrollManager({
                ref: this.listRef,
                ready: () => true,
                bounds: () => ({ start: 0, end: 1 }),
                getPosition: () => this.position,
                setPosition: (position) => (this.position = position),
                getItemEl: () => undefined,
                onNotReady: () => {},
                onSmoothScrollEnd: () => expect.step(`smooth scroll end at ${this.position}`),
            });
        }
    }
    await mountWithCleanup(List);
    expect.verifySteps(["smooth scroll end at bottom"]);
});
