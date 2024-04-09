import { test, expect, beforeEach, describe } from "@odoo/hoot";
import { click, press, queryAll, queryAllTexts, queryOne } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { getService, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { Dialog } from "@web/core/dialog/dialog";
import { Component, xml } from "@odoo/owl";
import { usePopover } from "@web/core/popover/popover_hook";
import { useAutofocus } from "@web/core/utils/hooks";
import { MainComponentsContainer } from "@web/core/main_components_container";

describe.current.tags("desktop");

beforeEach(async () => {
    await mountWithCleanup(MainComponentsContainer);
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
    click(".o_dialog footer button");
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

    // Call a second time, the close on the dialog.
    // As the dialog is already close, this call is just ignored. No error should be raised.
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
    click(".o_dialog footer button");
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
        getService("ui").activeElement
    );

    getService("dialog").add(CustomDialog, { title: "Sauron" });
    await animationFrame();
    expect(queryOne(".o_dialog:not(.o_inactive_modal) .modal")).toBe(
        getService("ui").activeElement
    );

    getService("dialog").add(CustomDialog, { title: "Rafiki" });
    await animationFrame();
    expect(queryOne(".o_dialog:not(.o_inactive_modal) .modal")).toBe(
        getService("ui").activeElement
    );
});

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

    expect(document).toBe(getService("ui").activeElement);
    expect(document.body).toBeFocused();

    getService("dialog").add(CustomDialog, { title: "Hello" });
    await animationFrame();
    expect(queryOne(".o_dialog:not(.o_inactive_modal) .modal")).toBe(
        getService("ui").activeElement
    );
    expect(".btn.o-default-button").toBeFocused();

    click(".btn.test");
    await animationFrame();
    expect(queryOne(".o_popover")).toBe(getService("ui").activeElement);
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

    press("Escape", { bubbles: true });
    await animationFrame();

    expect(".o_dialog").toHaveCount(2);
    res = activity(queryAll(".o_dialog"));
    expect(res.active).toEqual([false, true]);
    expect(res.names).toEqual(["Hello", "Sauron"]);

    click(".o_dialog:not(.o_inactive_modal) footer button");
    await animationFrame();

    expect(".o_dialog").toHaveCount(1);
    res = activity(queryAll(".o_dialog"));
    expect(res.active).toEqual([true]);
    expect(res.names).toEqual(["Hello"]);

    click("footer button");
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
    expect(["Error: Some Error"]).toVerifyErrors();
});
