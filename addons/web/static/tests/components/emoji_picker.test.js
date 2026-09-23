// @ts-check

import { expect, test } from "@odoo/hoot";
import { click, hover, press, queryAll, waitFor, waitUntil } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { Component, onRendered, reactive, useRef, useState, xml } from "@odoo/owl";
import { mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";
import {
    EmojiPicker,
    loadEmoji,
    loader,
    resetLoadedEmojiData,
    useEmojiPicker,
} from "@web/components/emoji_picker/emoji_picker";
import { browser } from "@web/core/browser/browser";

test("frequent emojis with unknown codepoints do not crash the picker", async () => {
    browser.localStorage.setItem(
        "web.emoji.frequent",
        JSON.stringify({ "<removed codepoints>": 5, "😀": 2 }),
    );
    await mountWithCleanup(EmojiPicker, { props: { onSelect: () => {} } });
    expect(".o-EmojiPicker").toHaveCount(1);
    expect(".o-EmojiPicker-content .o-Emoji[data-category='0']").toHaveCount(1);
    expect(".o-EmojiPicker-content .o-Emoji[data-category='0']").toHaveText("😀");
});

test("fallback UI is displayed when the emoji bundle fails to load", async () => {
    await resetLoadedEmojiData();
    patchWithCleanup(loader, {
        loadEmoji: () => Promise.reject(new Error("bundle load failure")),
    });
    await mountWithCleanup(EmojiPicker, { props: { onSelect: () => {} } });
    expect(".o-EmojiPicker").toHaveCount(1);
    expect(".o-EmojiPicker span.text-muted").toHaveText("Failed to load emojis...");
    expect(".o-EmojiPicker input").toHaveCount(0);
});

test.tags("mobile");
test("mobile picker dialog is torn down with its owner", async () => {
    /** @type {ReturnType<typeof useEmojiPicker>} */
    let picker;
    class Host extends Component {
        static template = xml`<div class="test-host"/>`;
        static props = ["*"];
        setup() {
            picker = useEmojiPicker(null, {
                onSelect: () => {},
                onClose: () => expect.step("closed"),
            });
        }
    }
    class Parent extends Component {
        static components = { Host };
        static template = xml`<Host t-if="this.state.show"/>`;
        static props = ["*"];
        setup() {
            this.state = useState({ show: true });
        }
    }
    const parent = await mountWithCleanup(Parent);

    picker.open();
    await waitFor(".modal .o-EmojiPicker");

    parent.state.show = false;
    await animationFrame();
    await animationFrame();
    expect(".modal").toHaveCount(0);
    expect(".o-EmojiPicker").toHaveCount(0);
    expect.verifySteps(["closed"]);
});

test.tags("mobile");
test("mobile picker app is torn down with its owner", async () => {
    class Host extends Component {
        static template = xml`<button class="test-toggler" t-ref="toggler">toggle</button>`;
        static props = ["*"];
        setup() {
            useEmojiPicker(useRef("toggler"), {
                onSelect: () => {},
                onClose: () => expect.step("closed"),
            });
        }
    }
    class Parent extends Component {
        static components = { Host };
        static template = xml`<Host t-if="this.state.show"/>`;
        static props = ["*"];
        setup() {
            this.state = useState({ show: true });
        }
    }
    const parent = await mountWithCleanup(Parent);

    await click(".test-toggler");
    await waitFor(".o-EmojiPicker");

    parent.state.show = false;
    await animationFrame();
    expect(".o-EmojiPicker").toHaveCount(0);
    expect.verifySteps(["closed"]);
});

test("the active emoji is read from the rendered list, not from the DOM", async () => {
    patchWithCleanup(loader, { loadEmoji: () => Promise.resolve([]) });
    /** @type {any} */
    let instance;
    class Probe extends EmojiPicker {
        setup() {
            super.setup();
            instance = this;
        }
    }
    await mountWithCleanup(Probe, { props: { onSelect: () => {} } });
    await animationFrame();

    const matchesList = () =>
        instance.activeEmoji?.codepoints ===
        instance.getEmojisFromSearch()[instance.state.activeEmojiIndex]?.codepoints;

    expect(matchesList()).toBe(true);

    instance.handleNavigation("ArrowRight");
    await animationFrame();
    expect(matchesList()).toBe(true);

    instance.gridRef = { el: null };
    expect(() => instance.activeEmoji).not.toThrow();
});

test.tags("desktop");
test("hovering an emoji updates the placeholder without re-rendering the grid", async () => {
    let renders = 0;
    class Probe extends EmojiPicker {
        setup() {
            super.setup();
            onRendered(() => renders++);
        }
    }
    const picker = await mountWithCleanup(Probe, { props: { onSelect: () => {} } });
    const cells = queryAll(".o-EmojiPicker-content .o-Emoji");
    expect(cells.length).toBeGreaterThan(1);

    renders = 0;
    await hover(cells[3]);
    await animationFrame();

    expect(renders).toBe(0);
    expect(".o-EmojiPicker input").toHaveAttribute(
        "placeholder",
        picker.getEmojisFromSearch()[3].shortcodes.join(" "),
    );

    await hover(cells[3].firstElementChild);
    await animationFrame();
    expect(".o-EmojiPicker input").toHaveAttribute(
        "placeholder",
        picker.getEmojisFromSearch()[3].shortcodes.join(" "),
    );

    await hover(".o-EmojiPicker-navbar");
    await animationFrame();
    expect(".o-EmojiPicker input").toHaveAttribute(
        "placeholder",
        picker.getEmojisFromSearch()[0].shortcodes.join(" "),
    );
});

test("the picker mounts in two renders: the navbar's first resize notification adds none", async () => {
    await loadEmoji();
    let renders = 0;
    class Probe extends EmojiPicker {
        setup() {
            super.setup();
            onRendered(() => renders++);
        }
    }
    const picker = await mountWithCleanup(Probe, { props: { onSelect: () => {} } });
    await animationFrame();
    await animationFrame();
    expect(picker.state.emojiNavbarRepr).not.toBe(undefined);
    expect(renders).toBe(2);
});

test("searching and scrolling never build the keyboard grid; the first arrow key does, once", async () => {
    await loadEmoji();
    let builds = 0;
    /** @type {any} */
    let picker;
    class Probe extends EmojiPicker {
        setup() {
            super.setup();
            picker = this;
        }
        computeEmojiMatrix() {
            builds++;
            return super.computeEmojiMatrix();
        }
    }
    await mountWithCleanup(Probe, { props: { onSelect: () => {} } });
    await animationFrame();
    expect(builds).toBe(0);

    picker.state.searchTerm = "ca";
    await animationFrame();
    await animationFrame();
    picker.state.searchTerm = "";
    await animationFrame();
    await animationFrame();
    picker.state.categoryId = picker.categories[2].sortId;
    await animationFrame();
    expect(builds).toBe(0);
    expect(".o-EmojiPicker input").not.toHaveAttribute("model");

    picker.handleNavigation("ArrowRight");
    picker.handleNavigation("ArrowDown");
    await animationFrame();
    expect(builds).toBe(1);
    expect(picker.state.activeEmojiIndex).not.toBe(0);
});

test("the grid listens for its cells: mounting them adds three listeners, not three per cell", async () => {
    await loadEmoji();
    const counts = {
        click: 0,
        mouseover: 0,
        mouseout: 0,
        mouseenter: 0,
        mouseleave: 0,
    };
    const { addEventListener } = EventTarget.prototype;
    patchWithCleanup(EventTarget.prototype, {
        /** @type {typeof addEventListener} */
        addEventListener(type, listener, options) {
            if (type in counts) {
                counts[type]++;
            }
            return addEventListener.call(this, type, listener, options);
        },
    });
    await mountWithCleanup(EmojiPicker, { props: { onSelect: () => {} } });
    const cells = queryAll(".o-EmojiPicker-content .o-Emoji").length;
    expect(cells).toBeGreaterThan(1000);
    expect(counts.mouseenter + counts.mouseleave).toBe(0);
    expect(counts.click + counts.mouseover + counts.mouseout).toBeLessThan(cells);

    await click(".o-EmojiPicker-content .o-Emoji:eq(5)");
    await animationFrame();
    expect(counts.click + counts.mouseover + counts.mouseout).toBeLessThan(cells);
});

test("adaptNavbar survives a navbar with no emoji rendered", async () => {
    /** @type {EmojiPicker} */
    let picker;
    patchWithCleanup(EmojiPicker.prototype, {
        setup() {
            super.setup();
            picker = this;
        },
    });
    await mountWithCleanup(EmojiPicker, { props: { onSelect: () => {} } });
    await animationFrame();

    const navbar = picker.navbarRef.el;
    expect(navbar.querySelectorAll(".o-Emoji").length).toBeGreaterThan(0);
    for (const el of [...navbar.querySelectorAll(".o-Emoji")]) {
        el.remove();
    }
    expect(() => picker.adaptNavbar()).not.toThrow();
});

test("category id stays a number when a search returns nothing", async () => {
    /** @type {Probe} */
    let picker;
    class Probe extends EmojiPicker {
        setup() {
            super.setup();
            picker = this;
        }
    }
    await mountWithCleanup(Probe, { props: { onSelect: () => {} } });
    await animationFrame();
    picker.state.searchTerm = "zzzzqqqqxxxx";
    await animationFrame();
    expect(".o-EmojiPicker-content .o-Emoji").toHaveCount(0);
    picker.highlightActiveCategory();
    await animationFrame();
    expect(Number.isNaN(picker.state.categoryId)).toBe(false);
});

test("external state search rebuilds the navigation grid", async () => {
    const external = reactive({ searchTerm: "" });
    let picker;
    class Probe extends EmojiPicker {
        setup() {
            super.setup();
            picker = this;
        }
    }
    class Parent extends Component {
        static components = { EmojiPicker: Probe };
        static props = ["*"];
        static template = xml`<EmojiPicker onSelect="() => {}" state="this.props.st"/>`;
    }
    await mountWithCleanup(Parent, { props: { st: external } });
    await animationFrame();

    external.searchTerm = "cat";
    await animationFrame();
    await animationFrame();
    const cells = () => picker.emojiMatrix.reduce((n, row) => n + row.length, 0);
    expect(cells()).toBe(queryAll(".o-EmojiPicker-content .o-Emoji").length);

    external.searchTerm = "flag";
    await animationFrame();
    await animationFrame();
    expect(cells()).toBe(queryAll(".o-EmojiPicker-content .o-Emoji").length);
});

test("the merged emoji list is not rebuilt on every render", async () => {
    /** @type {Probe} */
    let picker;
    class Probe extends EmojiPicker {
        setup() {
            super.setup();
            picker = this;
        }
    }
    await mountWithCleanup(Probe, { props: { onSelect: () => {} } });
    await animationFrame();
    const before = picker.getEmojisFromSearch();
    picker.render();
    await animationFrame();
    expect(picker.getEmojisFromSearch()).toBe(before);
});

test("every cell with a neighbouring row can be left with an arrow key", async () => {
    /** @type {Probe} */
    let picker;
    class Probe extends EmojiPicker {
        setup() {
            super.setup();
            picker = this;
        }
    }
    await mountWithCleanup(Probe, { props: { onSelect: () => {} } });
    await animationFrame();

    for (const searchTerm of ["", "cat", "a"]) {
        picker.state.searchTerm = searchTerm;
        await animationFrame();
        await animationFrame();
        const matrix = picker.emojiMatrix;
        const stuck = [];
        for (const [rowIndex, row] of matrix.entries()) {
            for (const [colIndex, index] of row.entries()) {
                for (const [key, step] of /** @type {[string, number][]} */ ([
                    ["ArrowDown", 1],
                    ["ArrowUp", -1],
                ])) {
                    if (!matrix[rowIndex + step]) {
                        continue;
                    }
                    picker.state.activeEmojiIndex = index;
                    picker.handleNavigation(key);
                    if (picker.state.activeEmojiIndex === index) {
                        stuck.push(
                            `${searchTerm || "<all>"} ${key} @${rowIndex},${colIndex}`,
                        );
                    }
                }
            }
        }
        expect(stuck).toEqual([]);
    }
});

test.tags("desktop");
test("an externally driven search brings the keyboard selection back in range", async () => {
    const external = reactive({ searchTerm: "" });
    /** @type {Probe} */
    let picker;
    class Probe extends EmojiPicker {
        setup() {
            super.setup();
            picker = this;
        }
    }
    class Parent extends Component {
        static components = { EmojiPicker: Probe };
        static props = ["*"];
        static template = xml`<EmojiPicker onSelect="(codepoints) => this.props.onSelect(codepoints)" state="this.props.st"/>`;
    }
    await mountWithCleanup(Parent, {
        props: { st: external, onSelect: (codepoints) => expect.step(codepoints) },
    });
    await animationFrame();

    picker.state.activeEmojiIndex = 300;
    external.searchTerm = "cat";
    await animationFrame();
    await animationFrame();

    const cells = queryAll(".o-EmojiPicker-content .o-Emoji");
    expect(cells.length).toBeGreaterThan(0);
    expect(cells.length).toBeLessThan(300);
    expect(picker.activeEmoji).not.toBe(undefined);

    await press("enter");
    await animationFrame();
    expect.verifySteps([picker.getEmojisFromSearch()[0].codepoints]);
});

test("the keyboard grid is rebuilt when the picker is resized", async () => {
    /** @type {any} */
    let picker;
    class Probe extends EmojiPicker {
        setup() {
            super.setup();
            picker = this;
        }
    }
    class Parent extends Component {
        static props = ["*"];
        static components = { Probe };
        static template = xml`
            <div t-attf-style="width: {{this.state.width}}px">
                <Probe onSelect="() => {}"/>
            </div>
        `;
        setup() {
            this.state = useState({ width: 400 });
        }
    }
    const parent = await mountWithCleanup(Parent);
    await animationFrame();

    const domRow = () => {
        const els = queryAll(".o-EmojiPicker-content .o-Emoji");
        const top = els[0]?.offsetTop;
        return els
            .filter((el) => el.offsetTop === top)
            .map((el) => Number.parseInt(el.dataset.index, 10));
    };

    expect(picker.emojiMatrix[0]).toEqual(domRow());
    const widthBefore = picker.emojiMatrix[0].length;

    parent.state.width = 180;
    await animationFrame();
    await animationFrame();

    expect(picker.emojiMatrix[0].length).not.toBe(widthBefore);
    expect(picker.emojiMatrix[0]).toEqual(domRow());
});

test("the keyboard grid is rebuilt when picking an emoji grows the recents", async () => {
    /** @type {any} */
    let picker;
    class Probe extends EmojiPicker {
        setup() {
            super.setup();
            picker = this;
        }
    }
    await mountWithCleanup(Probe, { props: { onSelect: () => false } });
    await animationFrame();

    for (const codepoints of Object.keys(picker.frequentEmojiService.all)) {
        delete picker.frequentEmojiService.all[codepoints];
    }
    await waitUntil(() => picker.recentEmojis.length === 0);
    await animationFrame();

    const domRow = () => {
        const els = queryAll(".o-EmojiPicker-content .o-Emoji");
        const top = els[0]?.offsetTop;
        return els
            .filter((el) => el.offsetTop === top)
            .map((el) => Number.parseInt(el.dataset.index, 10));
    };
    expect(picker.emojiMatrix[0]).toEqual(domRow());

    const before = queryAll(".o-EmojiPicker-content .o-Emoji").length;
    await click(".o-EmojiPicker-content .o-Emoji:eq(12)");
    await waitUntil(
        () => queryAll(".o-EmojiPicker-content .o-Emoji").length === before + 1,
    );
    await animationFrame();
    expect(picker.emojiMatrix[0]).toEqual(domRow());
});

test("resetting the emoji data also drops what was derived from it", async () => {
    await loadEmoji();
    expect(loader.loaded).not.toBe(undefined);
    const before = loader.loaded;

    await resetLoadedEmojiData();
    expect(loader.loaded).toBe(undefined);

    await loadEmoji();
    expect(loader.loaded).not.toBe(undefined);
    expect(loader.loaded).not.toBe(before);
});

test("keyboard navigation survives an emoji bundle that failed to load", async () => {
    await resetLoadedEmojiData();
    patchWithCleanup(loader, {
        loadEmoji: () => Promise.reject(new Error("bundle load failure")),
    });
    const picker = await mountWithCleanup(EmojiPicker, {
        props: { onSelect: () => {} },
    });
    expect(".o-EmojiPicker").toHaveCount(1);

    picker.handleNavigation("ArrowDown");
    picker.handleNavigation("ArrowUp");
    picker.handleNavigation("ArrowLeft");
    picker.handleNavigation("ArrowRight");
    expect(picker.state.activeEmojiIndex).toBe(0);
});
