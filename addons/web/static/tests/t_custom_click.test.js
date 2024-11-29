import { expect, test } from "@odoo/hoot";
import { middleClick, rightClick } from "@odoo/hoot-dom";
import { Component, xml } from "@odoo/owl";
import { contains, mountWithCleanup } from "@web/../tests/web_test_helpers";

test(`main button click`, async () => {
    class MyComponent extends Component {
        static template = xml`<div t-custom-click="plop" class="clickMe"><t t-esc="props.text"/></div>`;
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
        static template = xml`<div t-custom-click="plop" class="clickMe"><t t-esc="props.text"/></div>`;
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
        static template = xml`<div t-custom-click="plop" class="clickMe"><t t-esc="props.text"/></div>`;
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
        static template = xml`<div t-custom-click="plop" class="clickMe"><t t-esc="props.text"/></div>`;
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
        static template = xml`<div t-custom-click="(ev, isMiddleClick) => this.plop(ev, isMiddleClick, 'test')" class="clickMe"><t t-esc="props.text"/></div>`;
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
        static template = xml`<div t-custom-click="(ev, isMiddleClick) => this.plop(ev, isMiddleClick, 'test')" class="clickMe"><t t-esc="props.text"/></div>`;
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
        static template = xml`<div t-custom-click="(ev, isMiddleClick) => this.plop(ev, isMiddleClick, 'test')" class="clickMe"><t t-esc="props.text"/></div>`;
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
        static template = xml`<div t-on-click="noClick"><div t-custom-click.stop.prevent="plop" class="clickMe"><t t-esc="props.text"/></div></div>`;
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
        static template = xml`<div t-custom-click.synthetic="plop" class="clickMe"><t t-esc="props.text"/></div>`;
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
        static template = xml`<div t-custom-click="plop" class="clickMe"><t t-esc="props.text"/></div>`;
        static props = ["*"];
        plop() {
            expect.step("Shoudn't be called");
        }
    }

    await mountWithCleanup(MyComponent, { props: { text: "text from props" } });
    await rightClick(".clickMe");

    expect.verifySteps([]);
});
