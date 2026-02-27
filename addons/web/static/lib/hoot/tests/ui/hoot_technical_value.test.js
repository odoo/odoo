/** @odoo-module */

import { after, animationFrame, click, describe, expect, test } from "@odoo/hoot";
import { Component, signal, xml } from "@odoo/owl";
import { mountForTest, parseUrl } from "../local_helpers";

import { logger } from "../../core/logger";
import { HootTechnicalValue } from "../../ui/hoot_technical_value";

async function mountTechnicalValue(defaultValue) {
    function updateValue(newValue) {
        value.set(newValue);
        keyCounter.set(keyCounter() + 1);
        return animationFrame();
    }

    const value = signal(defaultValue);
    const keyCounter = signal(0);

    class TechnicalValueParent extends Component {
        static components = { HootTechnicalValue };
        static template = xml`<HootTechnicalValue t-key="this.keyCounter()" value="this.value()" />`;

        value = value;
        keyCounter = keyCounter;
    }

    await mountForTest(TechnicalValueParent);

    return updateValue;
}

describe(parseUrl(import.meta.url), () => {
    test("technical value with primitive values", async () => {
        const updateValue = await mountTechnicalValue("oui");
        expect(".hoot-string").toHaveText(`"oui"`);

        await updateValue(`"stringified"`);
        expect(".hoot-string").toHaveText(`'"stringified"'`);

        await updateValue(3);
        expect(".hoot-integer").toHaveText(`3`);

        await updateValue(undefined);
        expect(".hoot-undefined").toHaveText(`undefined`);

        await updateValue(null);
        expect(".hoot-null").toHaveText(`null`);
    });

    test("technical value with objects", async () => {
        const logDebug = logger.debug;
        logger.debug = expect.step;
        after(() => (logger.debug = logDebug));

        const updateValue = await mountTechnicalValue({});
        expect(".hoot-technical").toHaveText(`Object(0)`);

        await updateValue([1, 2, "3"]);

        expect(".hoot-technical").toHaveText(`Array(3)`);
        expect.verifySteps([]);

        await click(".hoot-object");
        await animationFrame();

        expect(".hoot-technical").toHaveText(`Array(3)[\n1\n,\n2\n,\n"3"\n,\n]`);
        expect.verifySteps([[1, 2, "3"]]);

        await updateValue({ a: true });
        expect(".hoot-technical").toHaveText(`Object(1)`);

        await click(".hoot-object");
        await animationFrame();

        expect(".hoot-technical").toHaveText(`Object(1){\na\n:\ntrue\n,\n}`);

        await updateValue({
            a: true,
            sub: {
                key: "oui",
            },
        });
        expect(".hoot-technical").toHaveText(`Object(2)`);

        await click(".hoot-object:first");
        await animationFrame();

        expect(".hoot-technical:first").toHaveText(
            `Object(2){\na\n:\ntrue\n,\nsub\n:\nObject(1)\n}`
        );
        expect.verifySteps([{ a: true }, { a: true, sub: { key: "oui" } }]);

        await click(".hoot-object:last");
        await animationFrame();

        expect(".hoot-technical:first").toHaveText(
            `Object(2){\na\n:\ntrue\n,\nsub\n:\nObject(1){\nkey\n:\n"oui"\n,\n}\n}`
        );
        expect.verifySteps([{ key: "oui" }]);
    });

    test("technical value with special cases", async () => {
        const updateValue = await mountTechnicalValue(new Date(0));
        expect(".hoot-technical").toHaveText(`1970-01-01T00:00:00.000Z`);

        await updateValue(/ab[c]/gi);
        expect(".hoot-technical").toHaveText(`/ab[c]/gi`);

        const def = Promise.withResolvers();
        await updateValue(def.promise);
        expect(".hoot-technical").toHaveText(`Promise<\npending\n>`);

        def.resolve("oui");
        await animationFrame();
        expect(".hoot-technical").toHaveText(`Promise<\nfulfilled\n:\n"oui"\n>`);
    });

    test("evaluation of unsafe value does not crash", async () => {
        const logDebug = logger.debug;
        logger.debug = () => expect.step("debug");
        after(() => (logger.debug = logDebug));

        class UnsafeString extends String {
            toString() {
                return this.valueOf();
            }
            valueOf() {
                throw new Error("UNSAFE");
            }
        }

        await mountTechnicalValue(new UnsafeString("some value"));
        await click(".hoot-object");

        expect(".hoot-object").toHaveText("UnsafeString(0)", {
            message: "size is 0 because it couldn't be evaluated",
        });

        expect.verifySteps(["debug"]);
    });
});
