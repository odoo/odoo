// @ts-check

import { destroy, expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { Component, reactive, useState, xml } from "@odoo/owl";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { useRecordObserver } from "@web/fields/hooks/record_observer";

/** @param {Record<string, any>} data */
function makeRecord(data) {
    return reactive({ data });
}

/**
 * @param {object} record
 * @returns {Promise<{ parent: any, parentState: any }>}
 */
async function mountObserver(record) {
    class Child extends Component {
        static template = xml`<span class="child"/>`;
        static props = ["record", "readonly"];
        setup() {
            useRecordObserver((rec, props) => {
                expect.step(`foo:${rec.data.foo}|readonly:${props.readonly}`);
            });
        }
    }
    class Parent extends Component {
        static components = { Child };
        static template = xml`
            <t t-if="this.state.mounted">
                <Child record="this.state.record" readonly="this.state.readonly"/>
            </t>`;
        static props = ["*"];
        setup() {
            this.state = useState({ record, readonly: false, mounted: true });
        }
    }
    const parent = await mountWithCleanup(Parent);
    return { parent, parentState: /** @type {any} */ (parent).state };
}

test("callback runs at setup and when an observed record value changes", async () => {
    const record = makeRecord({ foo: "abc" });
    const { parentState } = await mountObserver(record);
    expect.verifySteps(["foo:abc|readonly:false"]);

    parentState.record.data.foo = "def";
    await animationFrame();
    expect.verifySteps(["foo:def|readonly:false"]);
});

test("record swap re-arms the observer and fires with the new record", async () => {
    const oldRecord = makeRecord({ foo: "abc" });
    const { parentState } = await mountObserver(oldRecord);
    expect.verifySteps(["foo:abc|readonly:false"]);

    parentState.record = makeRecord({ foo: "swapped" });
    await animationFrame();
    expect.verifySteps(["foo:swapped|readonly:false"]);

    oldRecord.data.foo = "stale";
    await animationFrame();
    expect.verifySteps([]);
});

test("a prop-only update delivers fresh props to later invocations", async () => {
    const record = makeRecord({ foo: "abc" });
    const { parentState } = await mountObserver(record);
    expect.verifySteps(["foo:abc|readonly:false"]);

    parentState.readonly = true;
    await animationFrame();
    expect.verifySteps([]);

    parentState.record.data.foo = "def";
    await animationFrame();
    expect.verifySteps(["foo:def|readonly:true"]);
});

test("destroying the component during an in-flight batched call is safe", async () => {
    const record = makeRecord({ foo: "abc" });
    const { parent } = await mountObserver(record);
    expect.verifySteps(["foo:abc|readonly:false"]);

    record.data.foo = "def";
    destroy(parent);
    await animationFrame();
    expect.verifySteps([]);
    expect(".child").toHaveCount(0);
});

test("a rejection after the initial call is reported, not silently dropped", async () => {
    const record = makeRecord({ foo: "abc" });
    /** @type {any[]} */
    const errors = [];
    const originalError = console.error;
    console.error = (...args) => errors.push(args);

    class Child extends Component {
        static template = xml`<span class="child"/>`;
        static props = ["record"];
        setup() {
            useRecordObserver(async (rec) => {
                expect.step(`observed:${rec.data.foo}`);
                if (rec.data.foo === "boom") {
                    throw new Error("callback blew up");
                }
            });
        }
    }
    class Parent extends Component {
        static components = { Child };
        static template = xml`<Child record="this.state.record"/>`;
        static props = ["*"];
        setup() {
            this.state = useState({ record });
        }
    }
    try {
        await mountWithCleanup(Parent);
        expect.verifySteps(["observed:abc"]);

        record.data.foo = "boom";
        await animationFrame();
        await animationFrame();
        expect.verifySteps(["observed:boom"]);
        expect(errors.length).toBe(1);
        expect(String(errors[0][0])).toInclude("useRecordObserver");
        expect(String(errors[0][1])).toInclude("callback blew up");
    } finally {
        console.error = originalError;
    }
});
