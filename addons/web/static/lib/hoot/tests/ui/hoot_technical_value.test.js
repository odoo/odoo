/** @odoo-module */

import { describe, expect, mountOnFixture, test } from "@odoo/hoot";
import { click } from "@odoo/hoot-dom";
import { animationFrame, Deferred } from "@odoo/hoot-mock";
import { Component, reactive, useState, xml } from "@odoo/owl";
import { parseUrl } from "../local_helpers";

import { HootTechnicalValue } from "../../ui/hoot_technical_value";

const mountTechnicalValue = async (defaultValue) => {
    const updateValue = async (value) => {
        state.value = value;
        await animationFrame();
    };

    const state = reactive({ value: defaultValue });

    class TechnicalValueParent extends Component {
        static components = { HootTechnicalValue };
        static props = {};
        static template = xml`<HootTechnicalValue value="state.value" />`;

        setup() {
            this.state = useState(state);
        }
    }

    await mountOnFixture(TechnicalValueParent);

    return updateValue;
};

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
        const updateValue = await mountTechnicalValue({});
        expect(".hoot-technical").toHaveText(`Object(0)`);

        await updateValue([1, 2, "3"]);
        expect(".hoot-technical").toHaveText(`Array(3)`);

        await click(".hoot-object");
        await animationFrame();

        expect(".hoot-technical").toHaveText(`Array(3)[\n1\n,\n2\n,\n"3"\n,\n]`);

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

        await click(".hoot-object:last");
        await animationFrame();

        expect(".hoot-technical:first").toHaveText(
            `Object(2){\na\n:\ntrue\n,\nsub\n:\nObject(1){\nkey\n:\n"oui"\n,\n}\n}`
        );
    });

    test("technical value with special cases", async () => {
        const updateValue = await mountTechnicalValue(new Date(0));
        expect(".hoot-technical").toHaveText(`1970-01-01T00:00:00.000Z`);

        await updateValue(/ab[c]/gi);
        expect(".hoot-technical").toHaveText(`/ab[c]/gi`);

        const def = new Deferred(() => {});
        await updateValue(def);
        expect(".hoot-technical").toHaveText(`Deferred<\npending\n>`);

        def.resolve("oui");
        await animationFrame();
        expect(".hoot-technical").toHaveText(`Deferred<\nfulfilled\n:\n"oui"\n>`);
    });
});
