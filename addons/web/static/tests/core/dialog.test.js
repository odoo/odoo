import { destroy, expect, test } from "@odoo/hoot";
import { keyDown, keyUp, press, queryAllTexts, queryOne, resize } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { Component, onMounted, useState, xml } from "@odoo/owl";
import {
    contains,
    getService,
    makeDialogMockEnv,
    mountWithCleanup,
} from "@web/../tests/web_test_helpers";

import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";

test("simple rendering", async () => {
    expect.assertions(8);
    class Parent extends Component {
        static components = { Dialog };
        static template = xml`
            <Dialog title="'Wow(l) Effect'">
                Hello!
            </Dialog>
        `;
        static props = ["*"];
    }
    await makeDialogMockEnv();
    await mountWithCleanup(Parent);
    expect(".o_dialog").toHaveCount(1);
    expect(".o_dialog header .modal-title").toHaveCount(1, {
        message: "the header is rendered by default",
    });
    expect("header .modal-title").toHaveText("Wow(l) Effect");
    expect(".o_dialog main").toHaveCount(1, { message: "a dialog has always a main node" });
    expect("main").toHaveText("Hello!");
    expect(".o_dialog footer").toHaveCount(1, { message: "the footer is rendered by default" });
    expect(".o_dialog footer button").toHaveCount(1, {
        message: "the footer is rendered with a single button 'Ok' by default",
    });
    expect("footer button").toHaveText("Ok");
});

test("hotkeys work on dialogs", async () => {
    class Parent extends Component {
        static components = { Dialog };
        static template = xml`
            <Dialog title="'Wow(l) Effect'">
                Hello!
            </Dialog>
        `;
        static props = ["*"];
    }
    await makeDialogMockEnv({
        dialogData: {
            close: () => expect.step("close"),
            dismiss: () => expect.step("dismiss"),
        },
    });
    await mountWithCleanup(Parent);
    expect("header .modal-title").toHaveText("Wow(l) Effect");
    expect("footer button").toHaveText("Ok");
    // Same effect as clicking on the x button
    await press("escape");
    await animationFrame();
    expect.verifySteps(["dismiss", "close"]);
    // Same effect as clicking on the Ok button
    await keyDown("control+enter");
    await keyUp("ctrl+enter");
    expect.verifySteps(["close"]);
});

test("simple rendering with two dialogs", async () => {
    expect.assertions(3);
    class Parent extends Component {
        static template = xml`
            <div>
                <Dialog title="'First Title'">
                    Hello!
                </Dialog>
                <Dialog title="'Second Title'">
                    Hello again!
                </Dialog>
            </div>
        `;
        static props = ["*"];
        static components = { Dialog };
    }
    await makeDialogMockEnv();
    await mountWithCleanup(Parent);
    expect(".o_dialog").toHaveCount(2);
    expect(queryAllTexts("header .modal-title")).toEqual(["First Title", "Second Title"]);
    expect(queryAllTexts(".o_dialog .modal-body")).toEqual(["Hello!", "Hello again!"]);
});

test("click on the button x triggers the service close", async () => {
    expect.assertions(2);
    class Parent extends Component {
        static template = xml`
            <Dialog>
                Hello!
            </Dialog>
        `;
        static props = ["*"];
        static components = { Dialog };
    }
    await makeDialogMockEnv({
        dialogData: {
            close: () => expect.step("close"),
            dismiss: () => expect.step("dismiss"),
        },
    });
    await mountWithCleanup(Parent);
    expect(".o_dialog").toHaveCount(1);
    await contains(".o_dialog header button[aria-label='Close']").click();
    expect.verifySteps(["dismiss", "close"]);
});

test("click on the button x triggers the close and dismiss defined by a Child component", async () => {
    expect.assertions(2);
    class Child extends Component {
        static template = xml`<div>Hello</div>`;
        static props = ["*"];

        setup() {
            this.env.dialogData.close = () => expect.step("close");
            this.env.dialogData.dismiss = () => expect.step("dismiss");
            this.env.dialogData.scrollToOrigin = () => {};
        }
    }
    class Parent extends Component {
        static template = xml`
            <Dialog>
                <Child/>
            </Dialog>
        `;
        static props = ["*"];
        static components = { Child, Dialog };
    }
    await makeDialogMockEnv();
    await mountWithCleanup(Parent);
    expect(".o_dialog").toHaveCount(1);

    await contains(".o_dialog header button[aria-label='Close']").click();
    expect.verifySteps(["dismiss", "close"]);
});

test("click on the default footer button triggers the service close", async () => {
    expect.assertions(2);
    class Parent extends Component {
        static template = xml`
            <Dialog>
                Hello!
            </Dialog>
        `;
        static props = ["*"];
        static components = { Dialog };
    }
    await makeDialogMockEnv({
        dialogData: {
            close: () => expect.step("close"),
            dismiss: () => expect.step("dismiss"),
        },
    });
    await mountWithCleanup(Parent);
    expect(".o_dialog").toHaveCount(1);

    await contains(".o_dialog footer button").click();
    expect.verifySteps(["close"]);
});

test("render custom footer buttons is possible", async () => {
    expect.assertions(2);
    class SimpleButtonsDialog extends Component {
        static components = { Dialog };
        static template = xml`
            <Dialog>
                content
                <t t-set-slot="footer">
                    <div>
                        <button class="btn btn-primary">The First Button</button>
                        <button class="btn btn-primary">The Second Button</button>
                    </div>
                </t>
            </Dialog>
        `;
        static props = ["*"];
    }
    class Parent extends Component {
        static template = xml`
              <div>
                  <SimpleButtonsDialog/>
              </div>
          `;
        static props = ["*"];
        static components = { SimpleButtonsDialog };
        setup() {
            super.setup();
            this.state = useState({
                displayDialog: true,
            });
        }
    }
    await makeDialogMockEnv();
    await mountWithCleanup(Parent);
    expect(".o_dialog").toHaveCount(1);
    expect(".o_dialog footer button").toHaveCount(2);
});

test("embed an arbitrary component in a dialog is possible", async () => {
    expect.assertions(4);
    class SubComponent extends Component {
        static template = xml`
            <div class="o_subcomponent" t-esc="props.text" t-on-click="_onClick"/>
        `;
        static props = ["*"];
        _onClick() {
            expect.step("subcomponent-clicked");
            this.props.onClicked();
        }
    }
    class Parent extends Component {
        static components = { Dialog, SubComponent };
        static template = xml`
            <Dialog>
                <SubComponent text="'Wow(l) Effect'" onClicked="_onSubcomponentClicked"/>
            </Dialog>
        `;
        static props = ["*"];
        _onSubcomponentClicked() {
            expect.step("message received by parent");
        }
    }
    await makeDialogMockEnv();
    await mountWithCleanup(Parent);
    expect(".o_dialog").toHaveCount(1);
    expect(".o_dialog main .o_subcomponent").toHaveCount(1);
    expect(".o_subcomponent").toHaveText("Wow(l) Effect");
    await contains(".o_subcomponent").click();
    expect.verifySteps(["subcomponent-clicked", "message received by parent"]);
});

test("dialog without header/footer", async () => {
    expect.assertions(4);
    class Parent extends Component {
        static components = { Dialog };
        static template = xml`
            <Dialog header="false" footer="false">content</Dialog>
        `;
        static props = ["*"];
    }
    await makeDialogMockEnv();
    await mountWithCleanup(Parent);
    expect(".o_dialog").toHaveCount(1);
    expect(".o_dialog header").toHaveCount(0);
    expect("main").toHaveCount(1, { message: "a dialog has always a main node" });
    expect(".o_dialog footer").toHaveCount(0);
});

test("dialog size can be chosen", async () => {
    expect.assertions(5);
    class Parent extends Component {
        static template = xml`
            <div>
                <Dialog contentClass="'xl'" size="'xl'">content</Dialog>
                <Dialog contentClass="'lg'">content</Dialog>
                <Dialog contentClass="'md'" size="'md'">content</Dialog>
                <Dialog contentClass="'sm'" size="'sm'">content</Dialog>
            </div>
        `;
        static props = ["*"];
        static components = { Dialog };
    }
    await makeDialogMockEnv();
    await mountWithCleanup(Parent);
    expect(".o_dialog").toHaveCount(4);
    expect(".o_dialog .modal-dialog.modal-xl .xl").toHaveCount(1);
    expect(".o_dialog .modal-dialog.modal-lg .lg").toHaveCount(1);
    expect(".o_dialog .modal-dialog.modal-md .md").toHaveCount(1);
    expect(".o_dialog .modal-dialog.modal-sm .sm").toHaveCount(1);
});

test("dialog can be rendered on fullscreen", async () => {
    expect.assertions(2);
    class Parent extends Component {
        static template = xml`
            <Dialog fullscreen="true">content</Dialog>
        `;
        static props = ["*"];
        static components = { Dialog };
    }
    await makeDialogMockEnv();
    await mountWithCleanup(Parent);
    expect(".o_dialog").toHaveCount(1);
    expect(".o_dialog .modal").toHaveClass("o_modal_full");
});

test("can be the UI active element", async () => {
    expect.assertions(4);
    class Parent extends Component {
        static template = xml`<Dialog>content</Dialog>`;
        static props = ["*"];
        static components = { Dialog };
        setup() {
            this.ui = useService("ui");
            expect(this.ui.activeElement).toBe(document, {
                message:
                    "UI active element should be the default (document) as Parent is not mounted yet",
            });
            onMounted(() => {
                expect(".modal").toHaveCount(1);
                expect(this.ui.activeElement).toBe(
                    queryOne(".modal", { message: "UI active element should be the dialog modal" })
                );
            });
        }
    }
    await makeDialogMockEnv();
    const parent = await mountWithCleanup(Parent);
    destroy(parent);
    expect(getService("ui").activeElement).toBe(document, {
        message: "UI owner should be reset to the default (document)",
    });
});

test.tags("mobile");
test("dialog can't be moved on small screen", async () => {
    class Parent extends Component {
        static template = xml`<Dialog>content</Dialog>`;
        static components = { Dialog };
        static props = ["*"];
    }

    await makeDialogMockEnv();
    await mountWithCleanup(Parent);

    expect(".modal-content").toHaveStyle({
        top: "0px",
        left: "0px",
    });

    const header = queryOne(".modal-header");
    const headerRect = header.getBoundingClientRect();

    // Even if the `dragAndDrop` is called, confirms that there are no effects
    await contains(header).dragAndDrop(".modal-content", {
        position: {
            // the util function sets the source coordinates at (x; y) + (w/2; h/2)
            // so we need to move the dialog based on these coordinates.
            x: headerRect.x + headerRect.width / 2 + 20,
            y: headerRect.y + headerRect.height / 2 + 50,
        },
    });

    expect(".modal-content").toHaveStyle({
        top: "0px",
        left: "0px",
    });
});

test.tags("desktop");
test("dialog can be moved", async () => {
    class Parent extends Component {
        static template = xml`<Dialog>content</Dialog>`;
        static props = ["*"];
        static components = { Dialog };
    }
    await makeDialogMockEnv();
    await mountWithCleanup(Parent);
    expect(".modal-content").toHaveStyle({
        left: "0px",
        top: "0px",
    });

    const modalRect = queryOne(".modal").getBoundingClientRect();
    const header = queryOne(".modal-header");
    const headerRect = header.getBoundingClientRect();
    await contains(header).dragAndDrop(".modal-content", {
        position: {
            // the util function sets the source coordinates at (x; y) + (w/2; h/2)
            // so we need to move the dialog based on these coordinates.
            x: headerRect.x + headerRect.width / 2 + 20,
            y: headerRect.y + headerRect.height / 2 + 50,
        },
    });
    expect(".modal-content").toHaveStyle({
        left: `${modalRect.y + 20}px`,
        top: `${modalRect.x + 50}px`,
    });
});

test.tags("desktop");
test("dialog's position is reset on resize", async () => {
    class Parent extends Component {
        static template = xml`<Dialog>content</Dialog>`;
        static props = ["*"];
        static components = { Dialog };
    }
    await makeDialogMockEnv();
    await mountWithCleanup(Parent);
    expect(".modal-content").toHaveStyle({
        left: "0px",
        top: "0px",
    });

    const modalRect = queryOne(".modal").getBoundingClientRect();
    const header = queryOne(".modal-header");
    const headerRect = header.getBoundingClientRect();
    await contains(header).dragAndDrop(".modal-content", {
        position: {
            // the util function sets the source coordinates at (x; y) + (w/2; h/2)
            // so we need to move the dialog based on these coordinates.
            x: headerRect.x + headerRect.width / 2 + 20,
            y: headerRect.y + headerRect.height / 2 + 50,
        },
    });
    expect(".modal-content").toHaveStyle({
        left: `${modalRect.y + 20}px`,
        top: `${modalRect.x + 50}px`,
    });

    await resize();
    await animationFrame();
    expect(".modal-content").toHaveStyle({
        left: "0px",
        top: "0px",
    });
});
