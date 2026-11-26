import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { useVisible } from "@mail/utils/common/hooks";

import { describe, expect, test } from "@odoo/hoot";
import { tick, waitUntil } from "@odoo/hoot-dom";
import { Component, signal, xml } from "@odoo/owl";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("useVisible no longer reports the element visible once it is not ready", async () => {
    class Item extends Component {
        static template = xml`<div style="height: 50px" t-ref="this.itemRef"/>`;

        setup() {
            this.itemRef = signal.ref();
            this.visibleState = useVisible(this.itemRef, (isVisible) =>
                expect.step(`visible: ${isVisible}`)
            );
        }
    }
    const item = await mountWithCleanup(Item);
    await waitUntil(() => item.visibleState.isVisible);
    expect.verifySteps(["visible: true"]);
    item.visibleState.ready = false;
    await tick();
    expect(item.visibleState.isVisible).toBe(undefined);
    expect.verifySteps(["visible: undefined"]);
});

test("useVisible reads the visibility after a scroll the observer did not report yet", async () => {
    let item;
    let scrollAway = () => item.scrollableRef().scrollTo({ behavior: "instant", top: 400 });
    class Item extends Component {
        static template = xml`
            <div class="overflow-auto" style="height: 100px" t-ref="this.scrollableRef">
                <div style="height: 50px" t-ref="this.itemRef"/>
                <div style="height: 500px"/>
            </div>`;

        setup() {
            item = this;
            this.itemRef = signal.ref();
            this.scrollableRef = signal.ref();
            this.visibleState = useVisible(this.itemRef, (isVisible) => {
                if (isVisible && scrollAway) {
                    scrollAway();
                    scrollAway = null;
                }
            });
        }
    }
    const { promise, resolve } = Promise.withResolvers();
    document.addEventListener(
        "scrollend",
        () => resolve([item.visibleState.isVisible, item.visibleState.readVisibility()]),
        { capture: true, once: true }
    );
    await mountWithCleanup(Item);
    const [isVisibleOnScrollEnd, visibility] = await promise;
    expect(isVisibleOnScrollEnd).toBe(true);
    await expect(visibility).resolves.toBe(false);
    await waitUntil(() => item.visibleState.isVisible === false);
});
