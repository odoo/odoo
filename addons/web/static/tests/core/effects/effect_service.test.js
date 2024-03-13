import { Component, markup, xml } from "@odoo/owl";
import { animationFrame } from "@odoo/hoot-mock";
import { click, queryOne } from "@odoo/hoot-dom";
import { test, expect, beforeEach } from "@odoo/hoot";
import { user } from "@web/core/user";
import { patchWithCleanup, getService, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { MainComponentsContainer } from "@web/core/main_components_container";

let effectParams;

beforeEach(async () => {
    await mountWithCleanup(MainComponentsContainer);
    effectParams = {
        message: markup("<div>Congrats!</div>"),
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
    expect(queryOne(".o_reward_msg_content").innerHTML).toBe("<div>Congrats!</div>");

    const ev = new AnimationEvent("animationend", { animationName: "reward-fading-reverse" });
    queryOne(".o_reward").dispatchEvent(ev);
    await animationFrame();
    expect(".o_reward").toHaveCount(0);
});

test("rendering a rainbowman destroy on click", async () => {
    getService("effect").add(effectParams);
    await animationFrame();

    expect(".o_reward").toHaveCount(1);
    expect(".o_reward_rainbow").toHaveCount(1);

    click(".o_reward");
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
    expect.assertions(2);
    const props = { foo: "bar" };

    class Custom extends Component {
        static template = xml`<div class="custom">foo is <t t-esc="props.foo"/></div>`;
        static props = ["*"];
        setup() {
            expect(this.props).toEqual(props);
        }
    }

    getService("effect").add({ Component: Custom, props });
    await animationFrame();

    expect(queryOne(".o_reward_msg_content").innerHTML).toBe(
        `<div class="custom">foo is bar</div>`
    );
});
