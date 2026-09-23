// @ts-check

import { beforeEach, expect, test } from "@odoo/hoot";
import { click, manuallyDispatchProgrammaticEvent, queryOne } from "@odoo/hoot-dom";
import { advanceTime, animationFrame, runAllTimers } from "@odoo/hoot-mock";
import { Component, markup, xml } from "@odoo/owl";
import {
    getService,
    makeMockEnv,
    mountWithCleanup,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { user } from "@web/core/user";
import { MainComponentsContainer } from "@web/ui/main_components_container";

let effectParams;

beforeEach(async () => {
    await mountWithCleanup(MainComponentsContainer);
    effectParams = {
        message: markup`<div>Congrats!</div>`,
    };
});

test("effect service displays a rainbowman by default", async () => {
    getService("effect").add();
    await animationFrame();

    expect(".o_reward").toHaveCount(1);
    expect(".o_reward").toHaveText("Well Done!");
});

test("rainbowman effect with show_effect: false", async () => {
    patchWithCleanup(user, { showEffect: false });

    getService("effect").add();
    await animationFrame();

    expect(".o_reward").toHaveCount(0);
    expect(".o_notification").toHaveCount(1);
});

test("rendering a rainbowman destroy after animation", async () => {
    getService("effect").add(effectParams);
    await animationFrame();

    expect(".o_reward").toHaveCount(1);
    expect(".o_reward_rainbow").toHaveCount(1);
    expect(".o_reward_msg_content").toHaveInnerHTML("<div>Congrats!</div>");

    await manuallyDispatchProgrammaticEvent(queryOne(".o_reward"), "animationend", {
        animationName: "reward-fading-reverse",
    });
    await animationFrame();
    expect(".o_reward").toHaveCount(0);
});

test("rendering a rainbowman destroy on click", async () => {
    getService("effect").add(effectParams);
    await animationFrame();

    expect(".o_reward").toHaveCount(1);
    expect(".o_reward_rainbow").toHaveCount(1);

    await click(".o_reward");
    await animationFrame();
    expect(".o_reward").toHaveCount(0);
});

test("rendering a rainbowman with an escaped message", async () => {
    getService("effect").add(effectParams);
    await animationFrame();

    expect(".o_reward").toHaveCount(1);
    expect(".o_reward_rainbow").toHaveCount(1);
    expect(".o_reward_msg_content").toHaveText("Congrats!");
});

test("rendering a rainbowman with a custom component", async () => {
    expect.assertions(3);
    const props = { foo: "bar" };

    class Custom extends Component {
        static template = xml`<div class="custom">foo is <t t-out="this.props.foo"/></div>`;
        static props = ["*"];
        setup() {
            expect(this.props.foo).toBe(props.foo);
            expect(this.props.close).toBeInstanceOf(Function);
        }
    }

    getService("effect").add({ Component: Custom, props });
    await animationFrame();

    expect(".o_reward_msg_content").toHaveInnerHTML(
        `<div class="custom">foo is bar</div>`,
    );
});

test("a custom reward component can dismiss the reward", async () => {
    class Custom extends Component {
        static template = xml`<button class="dismiss" t-on-click="() => this.props.close()">Done</button>`;
        static props = ["*"];
    }

    getService("effect").add({ Component: Custom });
    await animationFrame();
    expect(".o_reward").toHaveCount(1);

    await click(".dismiss");
    await animationFrame();
    expect(".o_reward").toHaveCount(0);
});

test("a click inside a custom reward component does not dismiss it", async () => {
    class Custom extends Component {
        static template = xml`<button class="inert">Inert</button>`;
        static props = ["*"];
    }

    getService("effect").add({ Component: Custom });
    await animationFrame();
    expect(".o_reward").toHaveCount(1);

    await click(".inert");
    await animationFrame();
    expect(".o_reward").toHaveCount(1);
});

test("fadeout 'no' keeps the reward up until it is dismissed", async () => {
    getService("effect").add({ message: "Stay", fadeout: "no" });
    await animationFrame();
    expect(".o_reward").toHaveCount(1);

    await advanceTime(60_000);
    await animationFrame();
    expect(".o_reward").toHaveCount(1);
});

test("an unknown effect type is ignored rather than thrown", async () => {
    getService("effect").add({ type: "no_such_effect" });
    await runAllTimers();
    await animationFrame();
    expect(".o_reward").toHaveCount(0);
});

test("the reward message is announced, as it is when effects are off", async () => {
    getService("effect").add({ message: "Well Done!" });
    await animationFrame();
    expect(".o_reward_msg_content").toHaveAttribute("role", "status");
    expect(".o_reward_msg_content").toHaveText("Well Done!");
});

test("add() hands back a handle that dismisses the rainbowman", async () => {
    const close = getService("effect").add({ message: "Well done" });
    await animationFrame();
    expect(".o_reward").toHaveCount(1);

    expect(typeof close).toBe("function");
    close();
    await animationFrame();
    expect(".o_reward").toHaveCount(0);
});

test("add() hands back a handle on the notification fallback too", async () => {
    patchWithCleanup(user, { showEffect: false });
    const close = getService("effect").add({ message: "Well done" });
    await animationFrame();
    expect(".o_notification").toHaveCount(1);

    expect(typeof close).toBe("function");
    close();
    await animationFrame();
    expect(".o_notification").toHaveCount(0);
});

test("add() still returns a callable for an unknown effect type", async () => {
    const close = getService("effect").add({ type: "no_such_effect" });
    expect(typeof close).toBe("function");
    expect(() => close()).not.toThrow();
});

test("effect.add names the options it will not act on, like its siblings do", async () => {
    patchWithCleanup(odoo, { debug: "" });
    await makeMockEnv();
    /** @type {string[]} */
    const warnings = [];
    patchWithCleanup(console, {
        warn: (/** @type {string} */ message) => warnings.push(message),
    });

    getService("effect").add(
        { message: "Well done" },
        /** @type {any} */ ({ rootId: "somewhere", nonsense: 1 }),
    );

    expect(warnings.filter((w) => w.includes("nonsense"))).toHaveLength(1);
    expect(warnings.filter((w) => w.includes("rootId"))).toHaveLength(0);
});
