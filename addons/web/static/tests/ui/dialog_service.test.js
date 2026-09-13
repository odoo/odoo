// @ts-check

import { after, beforeEach, expect, getFixture, test } from "@odoo/hoot";
import { click, press, queryAll, queryAllTexts, queryOne } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { Component, xml } from "@odoo/owl";
import {
    getMockEnv,
    getService,
    mountWithCleanup,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";
import { useAutofocus } from "@web/core/utils/hooks";
import { Dialog } from "@web/ui/dialog/dialog";
import { DialogService } from "@web/ui/dialog/dialog_service";
import { MainComponentsContainer } from "@web/ui/main_components_container";
import { OverlayContainer } from "@web/ui/overlay/overlay_container";
import { rootIdOf } from "@web/ui/overlay/root_id";
import { usePopover } from "@web/ui/popover/popover_hook";

beforeEach(async () => {
    await mountWithCleanup(MainComponentsContainer);
});

test("closing one dialog service preserves the other service's body lock", async () => {
    class Content extends Component {
        static template = xml`<Dialog>content</Dialog>`;
        static components = { Dialog };
        static props = ["*"];
    }
    const first = getService("dialog");
    const second = new DialogService(getMockEnv(), { overlay: getService("overlay") });
    try {
        const closeFirst = first.add(Content);
        const closeSecond = second.add(Content);
        await animationFrame();
        await closeFirst();
        expect(document.body).toHaveClass("modal-open");
        await closeSecond();
        expect(document.body).not.toHaveClass("modal-open");
    } finally {
        second.destroy();
    }
});

test("Simple rendering with a single dialog", async () => {
    class CustomDialog extends Component {
        static components = { Dialog };
        static template = xml`<Dialog title="'Welcome'">content</Dialog>`;
        static props = ["*"];
    }
    expect(".o_dialog").toHaveCount(0);
    getService("dialog").add(CustomDialog);
    await animationFrame();
    expect(".o_dialog").toHaveCount(1);
    expect("header .modal-title").toHaveText("Welcome");
    await click(".o_dialog button");
    await animationFrame();
    expect(".o_dialog").toHaveCount(0);
});

test("Simple rendering and close a single dialog", async () => {
    class CustomDialog extends Component {
        static components = { Dialog };
        static template = xml`<Dialog title="'Welcome'">content</Dialog>`;
        static props = ["*"];
    }
    expect(".o_dialog").toHaveCount(0);
    const removeDialog = getService("dialog").add(CustomDialog);
    await animationFrame();
    expect(".o_dialog").toHaveCount(1);
    expect("header .modal-title").toHaveText("Welcome");

    removeDialog();
    await animationFrame();
    expect(".o_dialog").toHaveCount(0);

    removeDialog();
    expect(".o_dialog").toHaveCount(0);
});

test("rendering with two dialogs", async () => {
    class CustomDialog extends Component {
        static components = { Dialog };
        static template = xml`<Dialog title="props.title">content</Dialog>`;
        static props = ["*"];
    }
    expect(".o_dialog").toHaveCount(0);
    getService("dialog").add(CustomDialog, { title: "Hello" });
    await animationFrame();
    expect(".o_dialog").toHaveCount(1);
    expect("header .modal-title").toHaveText("Hello");

    getService("dialog").add(CustomDialog, { title: "Sauron" });
    await animationFrame();
    expect(".o_dialog").toHaveCount(2);
    expect(queryAllTexts("header .modal-title")).toEqual(["Hello", "Sauron"]);
    await click(".o_dialog button");
    await animationFrame();
    expect(".o_dialog").toHaveCount(1);
    expect("header .modal-title").toHaveText("Sauron");
});

test("multiple dialogs can become the UI active element", async () => {
    class CustomDialog extends Component {
        static components = { Dialog };
        static template = xml`<Dialog title="props.title">content</Dialog>`;
        static props = ["*"];
    }
    getService("dialog").add(CustomDialog, { title: "Hello" });
    await animationFrame();
    expect(queryOne(".o_dialog:not(.o_inactive_modal) .modal")).toBe(
        /** @type {any} */ (getService("ui").activeElement),
    );

    getService("dialog").add(CustomDialog, { title: "Sauron" });
    await animationFrame();
    expect(queryOne(".o_dialog:not(.o_inactive_modal) .modal")).toBe(
        /** @type {any} */ (getService("ui").activeElement),
    );

    getService("dialog").add(CustomDialog, { title: "Rafiki" });
    await animationFrame();
    expect(queryOne(".o_dialog:not(.o_inactive_modal) .modal")).toBe(
        /** @type {any} */ (getService("ui").activeElement),
    );
});

test.tags("desktop");
test("a popover with an autofocus child can become the UI active element", async () => {
    class TestPopover extends Component {
        static template = xml`<input type="text" t-ref="autofocus" />`;
        static props = ["*"];
        setup() {
            useAutofocus();
        }
    }
    class CustomDialog extends Component {
        static components = { Dialog };
        static template = xml`<Dialog title="props.title">
            <button class="btn test" t-on-click="showPopover">show</button>
        </Dialog>`;
        static props = ["*"];
        setup() {
            this.popover = usePopover(TestPopover);
        }
        showPopover(event) {
            this.popover.open(event.target, {});
        }
    }

    expect(document).toBe(/** @type {any} */ (getService("ui").activeElement));
    expect(document.body).toBeFocused();

    getService("dialog").add(CustomDialog, { title: "Hello" });
    await animationFrame();
    expect(queryOne(".o_dialog:not(.o_inactive_modal) .modal")).toBe(
        /** @type {any} */ (getService("ui").activeElement),
    );
    expect(".btn.test").toBeFocused();

    await click(".btn.test");
    await animationFrame();
    expect(queryOne(".o_popover")).toBe(
        /** @type {any} */ (getService("ui").activeElement),
    );
    expect(".o_popover input").toBeFocused();
});

test("Interactions between multiple dialogs", async () => {
    function activity(modals) {
        const active = [];
        const names = [];
        for (let i = 0; i < modals.length; i++) {
            active[i] = !modals[i].classList.contains("o_inactive_modal");
            names[i] = modals[i].querySelector(".modal-title").textContent;
        }
        return { active, names };
    }

    class CustomDialog extends Component {
        static components = { Dialog };
        static template = xml`<Dialog title="props.title">content</Dialog>`;
        static props = ["*"];
    }

    getService("dialog").add(CustomDialog, { title: "Hello" });
    await animationFrame();
    getService("dialog").add(CustomDialog, { title: "Sauron" });
    await animationFrame();
    getService("dialog").add(CustomDialog, { title: "Rafiki" });
    await animationFrame();

    expect(".o_dialog").toHaveCount(3);
    let res = activity(queryAll(".o_dialog"));
    expect(res.active).toEqual([false, false, true]);
    expect(res.names).toEqual(["Hello", "Sauron", "Rafiki"]);

    await press("Escape", { bubbles: true });
    await animationFrame();

    expect(".o_dialog").toHaveCount(2);
    res = activity(queryAll(".o_dialog"));
    expect(res.active).toEqual([false, true]);
    expect(res.names).toEqual(["Hello", "Sauron"]);

    await click(".o_dialog:not(.o_inactive_modal) button");
    await animationFrame();

    expect(".o_dialog").toHaveCount(1);
    res = activity(queryAll(".o_dialog"));
    expect(res.active).toEqual([true]);
    expect(res.names).toEqual(["Hello"]);

    await click(".o_dialog:not(.o_inactive_modal) button");
    await animationFrame();
    expect(".o_dialog").toHaveCount(0);
});

test("dialog component crashes", async () => {
    expect.errors(1);

    class FailingDialog extends Component {
        static components = { Dialog };
        static template = xml`<Dialog title="'Error'">content</Dialog>`;
        static props = ["*"];
        setup() {
            throw new Error("Some Error");
        }
    }

    getService("dialog").add(FailingDialog);
    await animationFrame();

    expect(".modal .o_error_dialog").toHaveCount(1);
    expect.verifyErrors(["Error: Some Error"]);
});

test("throwing onClose still cleans up stack and body class", async () => {
    class CustomDialog extends Component {
        static components = { Dialog };
        static template = xml`<Dialog title="'Boom'">content</Dialog>`;
        static props = ["*"];
    }
    const close = getService("dialog").add(
        CustomDialog,
        {},
        {
            onClose: () => {
                expect.step("onClose");
                throw new Error("onClose failed");
            },
        },
    );
    await animationFrame();
    expect(".o_dialog").toHaveCount(1);
    expect(document.body).toHaveClass("modal-open");

    await close().catch((error) => expect.step(error.message));
    await animationFrame();

    expect(".o_dialog").toHaveCount(0);
    expect(document.body).not.toHaveClass("modal-open");
    expect.verifySteps(["onClose", "onClose failed"]);
});

test("two dialogs, close the first one, closeAll", async () => {
    class CustomDialog extends Component {
        static components = { Dialog };
        static template = xml`<Dialog title="props.title">content</Dialog>`;
        static props = ["*"];
    }
    expect(".o_dialog").toHaveCount(0);
    const close = getService("dialog").add(CustomDialog, { title: "Hello" });
    await animationFrame();
    expect(".o_dialog").toHaveCount(1);
    expect("header .modal-title").toHaveText("Hello");

    getService("dialog").add(CustomDialog, { title: "Sauron" });
    await animationFrame();
    expect(".o_dialog").toHaveCount(2);
    expect(queryAllTexts("header .modal-title")).toEqual(["Hello", "Sauron"]);

    close();
    await animationFrame();
    expect(".o_dialog").toHaveCount(1);
    expect("header .modal-title").toHaveText("Sauron");

    getService("dialog").closeAll();
    await animationFrame();
    expect(".o_dialog").toHaveCount(0);
});

test("two dialogs, close the first one twice, then closeAll", async () => {
    class CustomDialog extends Component {
        static components = { Dialog };
        static template = xml`<Dialog title="props.title">content</Dialog>`;
        static props = ["*"];
    }
    expect(".o_dialog").toHaveCount(0);
    getService("dialog").add(
        CustomDialog,
        { title: "Hello" },
        {
            onClose: () => expect.step("close dialog 1"),
        },
    );
    await animationFrame();
    expect(".o_dialog").toHaveCount(1);
    expect("header .modal-title").toHaveText("Hello");
    expect(document.body).toHaveClass("modal-open");

    const close = getService("dialog").add(
        CustomDialog,
        { title: "Sauron" },
        {
            onClose: () => expect.step("close dialog 2"),
        },
    );
    await animationFrame();
    expect(".o_dialog").toHaveCount(2);
    expect(queryAllTexts("header .modal-title")).toEqual(["Hello", "Sauron"]);

    close();
    close();
    await animationFrame();
    expect(".o_dialog").toHaveCount(1);
    expect("header .modal-title").toHaveText("Hello");
    expect(document.body).toHaveClass("modal-open");
    expect.verifySteps(["close dialog 2"]);

    getService("dialog").closeAll();
    await animationFrame();
    expect(".o_dialog").toHaveCount(0);
    expect.verifySteps(["close dialog 1"]);
});

test.tags("mobile");
test("closing stacked dialogs restores the scroll position from before the first one", async () => {
    const scrollCalls = [];
    patchWithCleanup(browser, {
        scrollTo: (arg) => scrollCalls.push(arg),
    });
    const setScrollY = (value) =>
        Object.defineProperty(window, "scrollY", { value, configurable: true });

    class DialogComp extends Component {
        static template = xml`<Dialog><div class="mydialog">dialog</div></Dialog>`;
        static components = { Dialog };
        static props = ["*"];
    }

    setScrollY(500);
    const closeFirst = getService("dialog").add(DialogComp, {});
    await animationFrame();

    setScrollY(0);
    const closeSecond = getService("dialog").add(DialogComp, {});
    await animationFrame();

    closeFirst();
    await animationFrame();
    closeSecond();
    await animationFrame();

    expect(scrollCalls).toHaveLength(1);
    expect(scrollCalls[0].top).toBe(500);
});

test.tags("mobile");
test("closing dialogs across services restores scroll only after the last one", async () => {
    const scrollCalls = [];
    patchWithCleanup(browser, {
        scrollTo: (arg) => scrollCalls.push(arg),
    });
    const setScrollY = (value) =>
        Object.defineProperty(window, "scrollY", { value, configurable: true });

    class DialogComp extends Component {
        static template = xml`<Dialog><div class="mydialog">dialog</div></Dialog>`;
        static components = { Dialog };
        static props = ["*"];
    }

    const second = new DialogService(getMockEnv(), { overlay: getService("overlay") });
    after(() => second.destroy());
    setScrollY(500);
    const closeFirst = getService("dialog").add(DialogComp, {});
    await animationFrame();

    setScrollY(0);
    const closeSecond = second.add(DialogComp, {});
    await animationFrame();

    closeFirst();
    await animationFrame();
    expect(scrollCalls).toHaveLength(0);
    closeSecond();
    await animationFrame();

    expect(scrollCalls).toHaveLength(1);
    expect(scrollCalls[0].top).toBe(500);
});

test("a component overriding the header slot can reuse web.Dialog.header", async () => {
    class HeaderOverridingDialog extends Component {
        static components = { Dialog };
        static template = xml`
            <Dialog title="'Welcome'">
                <t t-set-slot="header" t-slot-scope="scope">
                    <t t-call="web.Dialog.header">
                        <t t-set="dismiss" t-value="scope.close"/>
                        <t t-set="fullscreen" t-value="scope.isFullscreen"/>
                        <t t-set="isClosing" t-value="scope.isClosing"/>
                        <t t-set="title" t-value="scope.title"/>
                        <t t-set="titleId" t-value="scope.titleId"/>
                    </t>
                    <button class="o_extra_header_button">Extra</button>
                </t>
                content
            </Dialog>`;
        static props = ["*"];
    }
    getService("dialog").add(HeaderOverridingDialog);
    await animationFrame();

    expect(".o_dialog").toHaveCount(1);
    expect("header .modal-title").toHaveText("Welcome");
    expect(".o_extra_header_button").toHaveCount(1);

    const labelledBy = queryOne("[role=dialog]").getAttribute("aria-labelledby");
    expect(labelledBy).toMatch(/^dialog_\d+_title$/);
    expect(`#${labelledBy}`).toHaveText("Welcome");

    await click(".o_dialog header [aria-label=Close]");
    await animationFrame();
    expect(".o_dialog").toHaveCount(0);
});

test("destroy() closes open dialogs and runs their onClose", async () => {
    class Body extends Component {
        static props = ["*"];
        static template = xml`<div class="destroy-probe"/>`;
    }
    let closed = 0;
    getService("dialog").add(Body, {}, { onClose: () => closed++ });
    await animationFrame();
    expect(".destroy-probe").toHaveCount(1);
    expect(document.body).toHaveClass("modal-open");

    getService("dialog").destroy();
    await animationFrame();

    expect(closed).toBe(1);
    expect(".destroy-probe").toHaveCount(0);
    expect(document.body).not.toHaveClass("modal-open");
});

test("only the topmost dialog claims aria-modal", async () => {
    class CustomDialog extends Component {
        static components = { Dialog };
        static template = xml`<Dialog title="props.title">content</Dialog>`;
        static props = ["*"];
    }
    const closers = [];
    for (const title of ["one", "two", "three"]) {
        closers.push(getService("dialog").add(CustomDialog, { title }));
        await animationFrame();
    }

    const modalState = () =>
        queryAll(".o_dialog .modal").map((m) => [
            m.querySelector(".modal-title").textContent,
            m.getAttribute("aria-modal"),
        ]);

    expect(modalState()).toEqual([
        ["one", null],
        ["two", null],
        ["three", "true"],
    ]);

    closers.at(-1)();
    await animationFrame();
    expect(modalState()).toEqual([
        ["one", null],
        ["two", "true"],
    ]);
});

test("closeAll settles only once every dialog has gone", async () => {
    class Slow extends Component {
        static template = xml`<Dialog title="'s'">body</Dialog>`;
        static components = { Dialog };
        static props = ["*"];
    }

    /** @type {(() => void)[]} */
    const releases = [];
    const slowClose = () =>
        new Promise((resolve) => releases.push(() => resolve(undefined)));

    getService("dialog").add(Slow, {}, { onClose: slowClose });
    getService("dialog").add(Slow, {}, { onClose: slowClose });
    await animationFrame();
    expect(".modal").toHaveCount(2);

    let settled = false;
    getService("dialog")
        .closeAll()
        .then(() => (settled = true));
    await animationFrame();
    expect(settled).toBe(false);
    expect(releases).toHaveLength(2);

    releases.forEach((release) => release());
    await animationFrame();
    await animationFrame();
    expect(settled).toBe(true);
    expect(".modal").toHaveCount(0);
});

test("the function add() hands back closes through the closing state", async () => {
    class CustomDialog extends Component {
        static components = { Dialog };
        static template = xml`<Dialog title="'Slow'">content</Dialog>`;
        static props = ["*"];
    }
    /** @type {(v?: any) => void} */
    let release = () => {};
    const blocked = new Promise((resolve) => (release = resolve));
    const close = getService("dialog").add(
        CustomDialog,
        {},
        { onClose: () => blocked },
    );
    await animationFrame();
    expect(".o_dialog").not.toHaveClass("o_dialog_closing");

    const closing = close();
    await animationFrame();
    expect(".o_dialog").toHaveClass("o_dialog_closing");
    expect(".modal-header button[aria-label='Close']").toHaveAttribute("disabled");

    release();
    await closing;
    await animationFrame();
    expect(".o_dialog").toHaveCount(0);
});

async function mountShadowOverlayContainer(hostId) {
    const { App } = await import("@odoo/owl");
    const { getTemplate } = await import("@web/core/templates");
    const host = document.createElement("div");
    host.id = hostId;
    getFixture().appendChild(host);
    const shadow = host.attachShadow({ mode: "open" });
    const overlays = getService("overlay").overlays;
    class ShadowHost extends Component {
        static components = { OverlayContainer };
        static props = {};
        static template = xml`<OverlayContainer overlays="overlays" rootId="rootId"/>`;
        setup() {
            this.overlays = overlays;
            this.rootId = hostId;
        }
    }
    const app = new App(ShadowHost, { env: getMockEnv(), getTemplate });
    await app.mount(shadow);
    return { app, shadow };
}

test("rootIdOf names the shadow host a node lives under", async () => {
    const { app, shadow } = await mountShadowOverlayContainer("chatterRoot");
    const inShadow = document.createElement("div");
    shadow.appendChild(inShadow);
    expect(rootIdOf(inShadow)).toBe("chatterRoot");
    expect(rootIdOf(getFixture())).toBe(undefined);
    expect(rootIdOf(null)).toBe(undefined);
    app.destroy();
});

test("a dialog opened with a rootId renders in that shadow root, not the page behind it", async () => {
    class CustomDialog extends Component {
        static components = { Dialog };
        static template = xml`<Dialog title="'Farewell'">content</Dialog>`;
        static props = ["*"];
    }
    const { app, shadow } = await mountShadowOverlayContainer("chatterRoot");

    getService("dialog").add(CustomDialog, {}, { rootId: "chatterRoot" });
    await animationFrame();

    expect(shadow.querySelectorAll(".o_dialog")).toHaveLength(1);
    expect(".o_dialog").toHaveCount(0);
    app.destroy();
});

test("a dialog opened with no rootId stays in the main document", async () => {
    class CustomDialog extends Component {
        static components = { Dialog };
        static template = xml`<Dialog title="'Farewell'">content</Dialog>`;
        static props = ["*"];
    }
    const { app, shadow } = await mountShadowOverlayContainer("chatterRoot");

    getService("dialog").add(CustomDialog);
    await animationFrame();

    expect(".o_dialog").toHaveCount(1);
    expect(shadow.querySelectorAll(".o_dialog")).toHaveLength(0);
    app.destroy();
});

test("dialogs from separate services have distinct IDs and accessible names", async () => {
    class Content extends Component {
        static template = xml`<Dialog title="props.title">content</Dialog>`;
        static components = { Dialog };
        static props = ["*"];
    }
    const second = new DialogService(getMockEnv(), { overlay: getService("overlay") });
    after(() => second.destroy());
    getService("dialog").add(Content, { title: "First owner" });
    second.add(Content, { title: "Second owner" });
    await animationFrame();
    expect(new Set(queryAll(".o_dialog").map((el) => el.id)).size).toBe(2);
    expect(
        queryAll(".modal").map((el) =>
            document
                .getElementById(el.getAttribute("aria-labelledby"))
                ?.textContent.trim(),
        ),
    ).toEqual(["First owner", "Second owner"]);
});

test("a failed dialog add preserves the active dialog and releases no extra body lock", async () => {
    class Content extends Component {
        static template = xml`<Dialog title="props.title">content</Dialog>`;
        static components = { Dialog };
        static props = ["*"];
    }
    const dialog = getService("dialog");
    const close = dialog.add(Content, { title: "Existing" });
    await animationFrame();
    const failure = new Error("Cannot build dialog props");
    expect(() =>
        dialog.add(Content, {
            get title() {
                throw failure;
            },
        }),
    ).toThrow(failure);
    expect(dialog.stack).toHaveLength(1);
    expect(dialog.stack[0].isActive).toBe(true);
    await close();
    expect(document.body).not.toHaveClass("modal-open");
});

test("a failed first dialog add does not acquire the body lock", async () => {
    class Content extends Component {
        static template = xml`<div/>`;
        static props = ["*"];
    }
    const failure = new Error("Cannot build dialog props");
    const dialog = getService("dialog");
    expect(() =>
        dialog.add(Content, {
            get title() {
                throw failure;
            },
        }),
    ).toThrow(failure);
    expect(dialog.stack).toHaveLength(0);
    expect(document.body).not.toHaveClass("modal-open");
});

test.tags("mobile");
test("destroying an idle service preserves another dialog's pending scroll restoration", async () => {
    const scrollCalls = [];
    patchWithCleanup(browser, { scrollTo: (position) => scrollCalls.push(position) });
    patchWithCleanup(window, { scrollY: 500 });
    class Content extends Component {
        static template = xml`<Dialog>content</Dialog>`;
        static components = { Dialog };
        static props = ["*"];
    }
    const idle = new DialogService(getMockEnv(), { overlay: getService("overlay") });
    after(() => idle.destroy());
    const close = getService("dialog").add(Content);
    await animationFrame();
    await close();
    expect(scrollCalls).toHaveLength(0);
    idle.destroy();
    await animationFrame();
    expect(scrollCalls).toEqual([{ top: 500, left: browser.scrollX }]);
});
