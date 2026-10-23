import { after, expect, test } from "@odoo/hoot";
import { middleClick, on, rightClick } from "@odoo/hoot-dom";
import { Component, xml } from "@odoo/owl";
import { contains, mountWithCleanup } from "@web/../tests/web_test_helpers";

test(`main button click`, async () => {
    class MyComponent extends Component {
        static template = xml`<div t-custom-click="plop" class="clickMe"><t t-out="this.props.text"/></div>`;
        static props = ["*"];
        plop(ev, isMiddleClick) {
            expect.step("clicked on plop");
            expect.step(`isMiddleClick: ${isMiddleClick}`);
        }
    }

    await mountWithCleanup(MyComponent, { props: { text: "text from props" } });

    expect(".clickMe").toHaveText("text from props");
    await contains(".clickMe").click();
    expect.verifySteps(["clicked on plop", "isMiddleClick: false"]);
});

test(`handler is bound`, async () => {
    class MyComponent extends Component {
        static template = xml`<div t-custom-click="plop" class="clickMe"><t t-out="this.props.text"/></div>`;
        static props = ["*"];
        setup() {
            this.test = "bind";
        }
        plop() {
            expect.step(this.test);
        }
    }

    await mountWithCleanup(MyComponent, { props: { text: "text from props" } });

    expect(".clickMe").toHaveText("text from props");
    await contains(".clickMe").click();
    expect.verifySteps(["bind"]);
});

test(`detect if middle Click`, async () => {
    class MyComponent extends Component {
        static template = xml`<div t-custom-click="plop" class="clickMe"><t t-out="this.props.text"/></div>`;
        static props = ["*"];
        plop(ev, isMiddleClick) {
            expect.step(`isMiddleClick: ${isMiddleClick}`);
        }
    }

    await mountWithCleanup(MyComponent, { props: { text: "text from props" } });
    await middleClick(".clickMe");

    expect.verifySteps(["isMiddleClick: true"]);
});

test(`detect if middle Click (ctrl+click)`, async () => {
    class MyComponent extends Component {
        static template = xml`<div t-custom-click="plop" class="clickMe"><t t-out="this.props.text"/></div>`;
        static props = ["*"];
        plop(ev, isMiddleClick) {
            expect.step(`isMiddleClick: ${isMiddleClick}`);
        }
    }

    await mountWithCleanup(MyComponent, { props: { text: "text from props" } });

    expect(".clickMe").toHaveText("text from props");
    await contains(".clickMe").click({ ctrlKey: true });
    expect.verifySteps(["isMiddleClick: true"]);
});

test(`main button (arrow function)`, async () => {
    class MyComponent extends Component {
        static template = xml`<div t-custom-click="(ev, isMiddleClick) => this.plop(ev, isMiddleClick, 'test')" class="clickMe"><t t-out="this.props.text"/></div>`;
        static props = ["*"];
        plop(ev, isMiddleClick, text) {
            expect.step(`clickend on plop`);
            expect.step(`text: ${text}`);
        }
    }

    await mountWithCleanup(MyComponent, { props: { text: "text from props" } });

    expect(".clickMe").toHaveText("text from props");
    await contains(".clickMe").click();
    expect.verifySteps(["clickend on plop", "text: test"]);
});

test(`handler is bound (arrow function)`, async () => {
    class MyComponent extends Component {
        static template = xml`<div t-custom-click="(ev, isMiddleClick) => this.plop(ev, isMiddleClick, 'test')" class="clickMe"><t t-out="this.props.text"/></div>`;
        static props = ["*"];
        setup() {
            this.test = "bind";
        }
        plop(ev, isMiddleClick, text) {
            expect.step(this.test);
            expect.step(`text: ${text}`);
        }
    }

    await mountWithCleanup(MyComponent, { props: { text: "text from props" } });

    expect(".clickMe").toHaveText("text from props");
    await contains(".clickMe").click();
    expect.verifySteps(["bind", "text: test"]);
});

test(`detect if middle Click (arrow function)`, async () => {
    class MyComponent extends Component {
        static template = xml`<div t-custom-click="(ev, isMiddleClick) => this.plop(ev, isMiddleClick, 'test')" class="clickMe"><t t-out="this.props.text"/></div>`;
        static props = ["*"];
        plop(ev, isMiddleClick, text) {
            expect.step(`isMiddleClick: ${isMiddleClick}`);
            expect.step(`text: ${text}`);
        }
    }

    await mountWithCleanup(MyComponent, { props: { text: "text from props" } });

    expect(".clickMe").toHaveText("text from props");
    await contains(".clickMe").click({ ctrlKey: true });
    expect.verifySteps(["isMiddleClick: true", "text: test"]);
});

test(`"stop" and "prevent" modifiers`, async () => {
    class MyComponent extends Component {
        static template = xml`<div t-on-click="this.noClick"><div t-custom-click.stop.prevent="plop" class="clickMe"><t t-out="this.props.text"/></div></div>`;
        static props = ["*"];
        plop(ev, isMiddleClick) {
            expect.step(`isMiddleClick: ${isMiddleClick}`);
            expect.step(`preventDefaulted: ${ev.defaultPrevented}`);
        }
        noClick() {
            expect.step("Shoudn't be called");
        }
    }

    await mountWithCleanup(MyComponent, { props: { text: "text from props" } });

    expect(".clickMe").toHaveText("text from props");
    await contains(".clickMe").click({ ctrlKey: true });
    expect.verifySteps(["isMiddleClick: true", "preventDefaulted: true"]);
});

test(`"synthetic" modifier`, async () => {
    class MyComponent extends Component {
        static template = xml`<div t-custom-click.synthetic="plop" class="clickMe"><t t-out="this.props.text"/></div>`;
        static props = ["*"];
        plop(ev) {
            expect(ev.currentTarget).toBe(document);
        }
    }

    await mountWithCleanup(MyComponent, { props: { text: "text from props" } });

    expect(".clickMe").toHaveText("text from props");
    await contains(".clickMe").click();
});

test(`Secondary button clicked`, async () => {
    class MyComponent extends Component {
        static template = xml`<div t-custom-click="plop" class="clickMe"><t t-out="this.props.text"/></div>`;
        static props = ["*"];
        plop() {
            expect.step("Shoudn't be called");
        }
    }

    await mountWithCleanup(MyComponent, { props: { text: "text from props" } });
    await rightClick(".clickMe");

    expect.verifySteps([]);
});

test.tags("desktop");
test(`middle button mousedown is default prevented`, async () => {
    class MyComponent extends Component {
        static template = xml`<div t-custom-click="plop" class="clickMe"><input class="editMe"/></div>`;
        static props = ["*"];
        plop(ev, isMiddleClick) {
            expect.step(`isMiddleClick: ${isMiddleClick}`);
        }
    }

    await mountWithCleanup(MyComponent);
    after(on(document, "mousedown", (ev) => {
        expect.step(`mousedown prevented: ${ev.defaultPrevented}`);
    }));

    await contains(".clickMe").click();
    expect.verifySteps(["mousedown prevented: false", "isMiddleClick: false"]);

    await middleClick(".clickMe");
    expect.verifySteps(["mousedown prevented: true", "isMiddleClick: true"]);

    // the browser default is kept in editable elements
    await middleClick(".editMe");
    expect.verifySteps(["mousedown prevented: false", "isMiddleClick: true"]);
});

test.tags("desktop");
test(`existing mousedown handler is kept`, async () => {
    class MyComponent extends Component {
        static template = xml`<div t-custom-click="plop" t-on-mousedown="onMouseDown" class="clickMe">text</div>`;
        static props = ["*"];
        plop(ev, isMiddleClick) {
            expect.step(`isMiddleClick: ${isMiddleClick}`);
        }
        onMouseDown() {
            expect.step("own mousedown");
        }
    }

    await mountWithCleanup(MyComponent);
    after(on(document, "mousedown", (ev) => {
        expect.step(`mousedown prevented: ${ev.defaultPrevented}`);
    }));

    await middleClick(".clickMe");
    expect.verifySteps(["own mousedown", "mousedown prevented: false", "isMiddleClick: true"]);
});

test.tags("desktop");
test(`existing mousedown handler with modifiers is kept`, async () => {
    class MyComponent extends Component {
        static template = xml`<div t-custom-click="plop" t-on-mousedown.capture="onMouseDown" class="clickMe">text</div>`;
        static props = ["*"];
        plop(ev, isMiddleClick) {
            expect.step(`isMiddleClick: ${isMiddleClick}`);
        }
        onMouseDown() {
            expect.step("own mousedown");
        }
    }

    await mountWithCleanup(MyComponent);
    after(on(document, "mousedown", (ev) => {
        expect.step(`mousedown prevented: ${ev.defaultPrevented}`);
    }));

    await middleClick(".clickMe");
    expect.verifySteps(["own mousedown", "mousedown prevented: false", "isMiddleClick: true"]);
});
