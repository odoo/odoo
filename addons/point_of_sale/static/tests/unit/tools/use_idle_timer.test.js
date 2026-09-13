import { Deferred, expect, getFixture, microTick, test } from "@odoo/hoot";
import { advanceTime } from "@odoo/hoot-mock";
import { App, Component, onWillStart, xml } from "@odoo/owl";
import { useIdleTimer } from "@point_of_sale/app/utils/use_idle_timer";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";

async function mountTimer(steps, onAlive = () => false) {
    class Timer extends Component {
        static props = {};
        static template = xml`<div/>`;
        setup() {
            useIdleTimer(steps, onAlive);
        }
    }
    return mountWithCleanup(Timer);
}

test("inactivity starts at the last activity, not the previous interval tick", async () => {
    await mountTimer([{ timeout: 1000, action: () => expect.step("idle") }]);
    await advanceTime(900);
    window.dispatchEvent(new MouseEvent("mousemove"));
    await advanceTime(200);
    expect.verifySteps([]);
    await advanceTime(800);
    expect.verifySteps(["idle"]);
});

test("fractional thresholds run in time order and idle suppresses later actions", async () => {
    await mountTimer([
        { timeout: 1500, action: () => expect.step("late") },
        {
            timeout: 500,
            action: () => {
                expect.step("early");
                return true;
            },
        },
    ]);
    await advanceTime(500);
    expect.verifySteps(["early"]);
    await advanceTime(1500);
    expect.verifySteps([]);
});

test("activity wakes the timer and rearms every threshold", async () => {
    await mountTimer(
        [
            {
                timeout: 1000,
                action: () => {
                    expect.step("idle");
                    return true;
                },
            },
        ],
        () => {
            expect.step("awake");
            return false;
        },
    );
    await advanceTime(1000);
    window.dispatchEvent(new MouseEvent("mousemove"));
    await advanceTime(1000);
    expect.verifySteps(["idle", "awake", "idle"]);
});

test("destroy cancels every pending threshold", async () => {
    const component = await mountTimer([
        { timeout: 1000, action: () => expect.step("idle") },
    ]);
    component.__owl__.app.destroy();
    await advanceTime(2000);
    expect.verifySteps([]);
});

test("a component destroyed before mounting cannot trigger idle actions", async () => {
    const ready = new Deferred();
    class Timer extends Component {
        static props = {};
        static template = xml`<div/>`;
        setup() {
            useIdleTimer([{ timeout: 1000, action: () => expect.step("idle") }]);
            onWillStart(() => ready);
        }
    }
    const app = new App(Timer);
    app.mount(getFixture());
    await microTick();
    app.destroy();
    ready.resolve();
    await advanceTime(2000);
    expect.verifySteps([]);
});

test("a declined idle action does not suppress the next threshold", async () => {
    await mountTimer([
        {
            timeout: 1000,
            action: () => {
                expect.step("declined");
                return false;
            },
        },
        {
            timeout: 2000,
            action: () => {
                expect.step("idle");
                return true;
            },
        },
    ]);
    await advanceTime(2000);
    expect.verifySteps(["declined", "idle"]);
});

test("destroying the component during wake does not rearm idle deadlines", async () => {
    const component = await mountTimer(
        [
            {
                timeout: 1000,
                action: () => {
                    expect.step("idle");
                    return true;
                },
            },
        ],
        () => {
            component.__owl__.app.destroy();
            return false;
        },
    );
    await advanceTime(1000);
    expect.verifySteps(["idle"]);
    window.dispatchEvent(new MouseEvent("mousemove"));
    await advanceTime(2000);
    expect.verifySteps([]);
});
