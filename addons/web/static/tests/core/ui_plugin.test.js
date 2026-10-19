import { render } from "@web/owl2/utils";
import { describe, expect, test } from "@odoo/hoot";
import { press, queryOne } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { Component, proxy, signal, xml } from "@odoo/owl";
import { getService, mountWithCleanup } from "../web_test_helpers";

import { MainComponentsContainer } from "@web/core/main_components_container";
import { UIPlugin, useActiveElement } from "@web/core/ui/ui_plugin";
import { useAutofocus } from "@web/core/utils/hooks";

describe.current.tags("desktop");

test("block and unblock once ui with ui service", async () => {
    await mountWithCleanup(MainComponentsContainer);
    expect(".o_blockUI").toHaveCount(0);
    getService(UIPlugin).block();
    await animationFrame();
    expect(".o_blockUI").toHaveCount(1);
    getService(UIPlugin).unblock();
    await animationFrame();
    expect(".o_blockUI").toHaveCount(0);
});

test("use block and unblock several times to block ui with ui service", async () => {
    await mountWithCleanup(MainComponentsContainer);
    expect(".o_blockUI").toHaveCount(0);
    getService(UIPlugin).block();
    getService(UIPlugin).block();
    getService(UIPlugin).block();
    await animationFrame();
    expect(".o_blockUI").toHaveCount(1);
    getService(UIPlugin).unblock();
    getService(UIPlugin).unblock();
    await animationFrame();
    expect(".o_blockUI").toHaveCount(1);
    getService(UIPlugin).unblock();
    await animationFrame();
    expect(".o_blockUI").toHaveCount(0);
});

test("a component can be the  UI active element: simple usage", async () => {
    class MyComponent extends Component {
        static template = xml`
            <div>
                <h1>My Component</h1>
                <div t-if="this.hasRef" id="owner" t-ref="this.delegatedRef">
                <input type="text"/>
            </div>
            </div>
        `;
        delegatedRef = signal.ref();
        setup() {
            useActiveElement(this.delegatedRef);
            this.hasRef = true;
        }
    }

    const comp = await mountWithCleanup(MyComponent);

    expect(getService(UIPlugin).activeElement()).toBe(queryOne("#owner"));
    expect("#owner input").toBeFocused();
    comp.hasRef = false;
    render(comp);
    await animationFrame();
    expect(getService(UIPlugin).activeElement()).toBe(document);
    expect(document.body).toBeFocused();
});

test("UI active element: trap focus", async () => {
    class MyComponent extends Component {
        static template = xml`
            <div>
                <h1>My Component</h1>
                <input type="text" placeholder="outerUIActiveElement"/>
                <div t-ref="this.delegatedRef">
                    <input type="text" placeholder="withFocus"/>
                </div>
            </div>
        `;
        delegatedRef = signal.ref();
        setup() {
            useActiveElement(this.delegatedRef);
        }
    }

    await mountWithCleanup(MyComponent);

    expect("input[placeholder=withFocus]").toBeFocused();
    let [firstEvent] = await press("Tab", { shiftKey: false });
    await animationFrame();
    expect(firstEvent.defaultPrevented).toBe(true);
    expect("input[placeholder=withFocus]").toBeFocused();

    [firstEvent] = await press("Tab", { shiftKey: true });
    await animationFrame();
    expect(firstEvent.defaultPrevented).toBe(true);
    expect("input[placeholder=withFocus]").toBeFocused();
});

test("UI active element: trap focus - default focus with autofocus", async () => {
    class MyComponent extends Component {
        static template = xml`
            <div>
                <h1>My Component</h1>
                <input type="text" placeholder="outerUIActiveElement"/>
                <div t-ref="this.delegatedRef">
                    <input type="text" placeholder="withoutFocus"/>
                    <input type="text" t-ref="this.autofocusRef" placeholder="withAutoFocus"/>
                </div>
            </div>
        `;
        delegatedRef = signal.ref();
        autofocusRef = signal.ref();
        setup() {
            useActiveElement(this.delegatedRef);
            useAutofocus({ ref: this.autofocusRef });
        }
    }

    await mountWithCleanup(MyComponent);

    expect("input[placeholder=withAutoFocus]").toBeFocused();
    let [firstEvent] = await press("Tab", { shiftKey: false });
    await animationFrame();
    expect(firstEvent.defaultPrevented).toBe(true);
    expect("input[placeholder=withoutFocus]").toBeFocused();

    [firstEvent] = await press("Tab", { shiftKey: true });
    await animationFrame();
    expect(firstEvent.defaultPrevented).toBe(true);
    expect("input[placeholder=withAutoFocus]").toBeFocused();

    [firstEvent] = await press("Tab", { shiftKey: true });
    await animationFrame();
    expect(firstEvent.defaultPrevented).toBe(false);
});

test("do not become UI active element if no element to focus", async () => {
    class MyComponent extends Component {
        static template = xml`
            <div>
                <h1>My Component</h1>
                <input type="text" placeholder="outerUIActiveElement"/>
                <div id="idActiveElement" t-ref="this.delegatedRef">
                    <div>
                        <span> No focus element </span>
                    </div>
                </div>
            </div>
        `;
        delegatedRef = signal.ref();
        setup() {
            useActiveElement(this.delegatedRef);
        }
    }

    await mountWithCleanup(MyComponent);
    expect(getService(UIPlugin).activeElement()).toBe(document);
});

test("become UI active element if no element to focus but the container is focusable", async () => {
    class MyComponent extends Component {
        static template = xml`
            <div>
                <h1>My Component</h1>
                <input type="text" placeholder="outerUIActiveElement"/>
                <div id="idActiveElement" t-ref="this.delegatedRef" tabindex="-1">
                    <div>
                        <span> No focus element </span>
                    </div>
                </div>
            </div>
        `;
        delegatedRef = signal.ref();
        setup() {
            useActiveElement(this.delegatedRef);
        }
    }

    await mountWithCleanup(MyComponent);
    expect(getService(UIPlugin).activeElement()).toBe(queryOne("#idActiveElement"));
});

test("UI active element: trap focus - first or last tabable changes", async () => {
    class MyComponent extends Component {
        static template = xml`
            <div>
                <h1>My Component</h1>
                <input type="text" name="outer"/>
                <div id="idActiveElement" t-ref="this.delegatedRef">
                    <div>
                        <input type="text" name="a" t-if="this.show.a"/>
                        <input type="text" name="b"/>
                        <input type="text" name="c" t-if="this.show.c"/>
                    </div>
                </div>
            </div>
        `;
        delegatedRef = signal.ref();
        setup() {
            this.show = proxy({ a: true, c: false });
            useActiveElement(this.delegatedRef);
        }
    }

    const comp = await mountWithCleanup(MyComponent);

    expect("input[name=a]").toBeFocused();

    let [firstEvent] = await press("Tab", { shiftKey: true });
    await animationFrame();
    expect(firstEvent.defaultPrevented).toBe(true);
    expect("input[name=b]").toBeFocused();

    comp.show.a = false;
    comp.show.c = true;
    await animationFrame();
    expect("input[name=b]").toBeFocused();

    [firstEvent] = await press("Tab", { shiftKey: true });
    await animationFrame();
    expect(firstEvent.defaultPrevented).toBe(true);
    expect("input[name=c]").toBeFocused();
});

test("UI active element: trap focus is not bypassed using invisible elements", async () => {
    class MyComponent extends Component {
        static template = xml`
            <div>
                <h1>My Component</h1>
                <input type="text" placeholder="outerUIActiveElement"/>
                <div t-ref="this.delegatedRef">
                    <input type="text" placeholder="withFocus"/>
                    <input class="d-none" type="text" placeholder="withFocusNotDisplayed"/>
                    <div class="d-none">
                        <input type="text" placeholder="withFocusNotDisplayedToo"/>
                    </div>
                </div>
            </div>
        `;
        delegatedRef = signal.ref();
        setup() {
            useActiveElement(this.delegatedRef);
        }
    }

    await mountWithCleanup(MyComponent);

    expect("input[placeholder=withFocus]").toBeFocused();

    let [firstEvent] = await press("Tab", { shiftKey: false });
    await animationFrame();
    expect(firstEvent.defaultPrevented).toBe(true);
    expect("input[placeholder=withFocus]").toBeFocused();

    [firstEvent] = await press("Tab", { shiftKey: true });
    await animationFrame();
    expect(firstEvent.defaultPrevented).toBe(true);
    expect("input[placeholder=withFocus]").toBeFocused();
});
