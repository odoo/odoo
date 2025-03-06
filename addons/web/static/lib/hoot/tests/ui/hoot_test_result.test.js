/** @odoo-module */

import { describe, expect, makeExpect, test } from "@odoo/hoot";
import { mountForTest, parseUrl } from "../local_helpers";

import { animationFrame, click } from "@odoo/hoot-dom";
import { Component, xml } from "@odoo/owl";
import { Runner } from "../../core/runner";
import { Test } from "../../core/test";
import { HootTestResult } from "../../ui/hoot_test_result";

/**
 * @param {(mockExpect: typeof expect) => any} callback
 */
const mountTestResults = async (testFn, props) => {
    const runner = new Runner();
    const mockTest = new Test(null, "test", {});
    const [mockExpect, { after, before }] = makeExpect({});

    class Parent extends Component {
        static components = { HootTestResult };
        static props = { test: Test, open: [Boolean, { value: "always" }] };
        static template = xml`
            <HootTestResult test="props.test" open="props.open">
                Toggle
            </HootTestResult>
        `;

        mockTest = mockTest;
    }

    before(mockTest);
    testFn(mockExpect);
    after(runner);

    await mountForTest(Parent, {
        env: { runner },
        props: {
            test: mockTest,
            open: "always",
            ...props,
        },
    });

    return mockTest;
};

const CLS_PASS = "text-emerald";
const CLS_FAIL = "text-rose";

describe(parseUrl(import.meta.url), () => {
    test("test results: toBe and basic interactions", async () => {
        const mockTest = await mountTestResults(
            (mockExpect) => {
                mockExpect(true).toBe(true);
                mockExpect(true).toBe(false);
            },
            { open: false }
        );

        expect(".HootTestResult button:only").toHaveText("Toggle");
        expect(".hoot-result-detail").not.toHaveCount();
        expect(mockTest.lastResults.pass).toBe(false);

        await click(".HootTestResult button");
        await animationFrame();

        expect(".hoot-result-detail").toHaveCount(1);

        // First assertion: pass
        expect(`.hoot-result-detail > .${CLS_PASS}`).toHaveText(
            /received value is strictly equal to true/,
            { inline: true }
        );

        // Second assertion: fail
        expect(`.hoot-result-detail > .${CLS_FAIL}`).toHaveText(
            /expected values to be strictly equal/,
            { inline: true }
        );
        expect(`.hoot-info .${CLS_PASS}:contains(Expected)`).toHaveCount(1);
        expect(`.hoot-info .${CLS_FAIL}:contains(Received)`).toHaveCount(1);
    });
    test("test results: toEqual", async () => {
        await mountTestResults((mockExpect) => {
            mockExpect([1, 2, { a: true }]).toEqual([1, 2, { a: true }]);
            mockExpect([1, { a: false }, 3]).toEqual([1, { a: true }, 3]);
        });

        expect(".hoot-result-detail").toHaveCount(1);

        // First assertion: pass
        expect(`.hoot-result-detail > .${CLS_PASS}`).toHaveText(
            /received value is deeply equal to \[1, 2, { a: true }\]/,
            { inline: true }
        );

        // Second assertion: fail
        expect(`.hoot-result-detail > .${CLS_FAIL}`).toHaveText(
            /expected values to be deeply equal/,
            { inline: true }
        );
        expect(`.hoot-info .${CLS_PASS}:contains(Expected)`).toHaveCount(1);
        expect(`.hoot-info .${CLS_FAIL}:contains(Received)`).toHaveCount(1);
    });

    test("test results: toHaveCount", async () => {
        await mountForTest(/* xml */ `
            <span class="text" >abc</span>
            <span class="text" >bcd</span>
        `);
        await mountTestResults((mockExpect) => {
            mockExpect(".text").toHaveCount(2);
            mockExpect(".text").toHaveCount(1);
        });

        expect(".hoot-result-detail").toHaveCount(1);

        // First assertion: pass
        expect(`.hoot-result-detail > .${CLS_PASS}`).toHaveText(
            /found 2 elements matching ".text"/,
            { inline: true }
        );

        // Second assertion: fail
        expect(`.hoot-result-detail > .${CLS_FAIL}`).toHaveText(
            /found 2 elements matching ".text"/,
            { inline: true }
        );
        expect(`.hoot-info .${CLS_PASS}:contains(Expected)`).toHaveCount(1);
        expect(`.hoot-info .${CLS_FAIL}:contains(Received)`).toHaveCount(1);
    });

    test("multiple test results: toHaveText", async () => {
        await mountForTest(/* xml */ `
            <span class="text" >abc</span>
            <span class="text" >bcd</span>
        `);
        await mountTestResults((mockExpect) => {
            mockExpect(".text:first").toHaveText("abc");
            mockExpect(".text").toHaveText("abc");
            mockExpect(".text").not.toHaveText("abc");
        });

        expect(".hoot-result-detail").toHaveCount(1);

        // First assertion: pass
        expect(`.hoot-result-detail > .${CLS_PASS}`).toHaveText(
            /1 element matching ".text:first" has text "abc"/,
            { inline: true }
        );

        // Second assertion: fail
        expect(`.hoot-result-detail > .${CLS_FAIL}:eq(0)`).toHaveText(
            /expected 2 elements matching ".text" to have the given text/,
            { inline: true }
        );
        expect(".hoot-info:eq(0) .hoot-html").toHaveCount(2);
        expect(".hoot-info:eq(0) .hoot-html").toHaveText("<span.text/>");
        expect(`.hoot-info:eq(0) .${CLS_PASS}:contains(Received)`).toHaveCount(1);
        expect(`.hoot-info:eq(0) .${CLS_PASS}:contains(Expected)`).toHaveCount(1);
        expect(`.hoot-info:eq(0) .${CLS_FAIL}:contains(Received)`).toHaveCount(1);

        // Third assertion: fail
        expect(`.hoot-result-detail > .${CLS_FAIL}:eq(1)`).toHaveText(
            /expected 2 elements matching ".text" not to have the given text/,
            { inline: true }
        );
        expect(".hoot-info:eq(1) .hoot-html").toHaveCount(2);
        expect(".hoot-info:eq(1) .hoot-html").toHaveText("<span.text/>");
        expect(`.hoot-info:eq(1) .${CLS_PASS}:contains(Received)`).toHaveCount(1);
        expect(`.hoot-info:eq(1) .${CLS_PASS}:contains(Expected)`).toHaveCount(1);
        expect(`.hoot-info:eq(1) .${CLS_FAIL}:contains(Received)`).toHaveCount(1);
    });
});
