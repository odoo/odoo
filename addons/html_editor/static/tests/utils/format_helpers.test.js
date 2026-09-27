import { describe, expect, test } from "@odoo/hoot";
import { unformat } from "../_helpers/format";
import { base64Img } from "../_helpers/editor";

describe("unformat", () => {
    test("should trim space between a tag name and an attribute", () => {
        expect(
            unformat(`<div
        class="something">`)
        ).toBe(`<div class="something">`);
    });
    test("should trim space at the beginning and end of the string", () => {
        expect(
            unformat(`
                <div>abc</div>
            `)
        ).toBe(`<div>abc</div>`);
    });
    test("should trim space between a node and its text content", () => {
        expect(
            unformat(
                `<div>
                    abc
                </div>`
            )
        ).toBe(`<div>abc</div>`);
    });
    test("should trim space between nodes", () => {
        expect(
            unformat(
                `<div>abc</div>
                <p>def</p>`
            )
        ).toBe(`<div>abc</div><p>def</p>`);
    });
    test("should not trim space between words in text content", () => {
        expect(unformat(`<div>some content</div>`)).toBe(`<div>some content</div>`);
    });
    test("should not remove feff characters", () => {
        expect(
            unformat(
                `<div>
                    text     \ufeff     
                </div>`
            )
        ).toBe(`<div>text     \ufeff</div>`);
    });
    test("should not remove spaces within an attribute", () => {
        const html = `<img src="${base64Img}" class="a  b"/>`;
        expect(unformat(html)).toBe(html);
    });
    test("should unformat a complex structure", () => {
        expect(
            unformat(`
                <div>
                    abc
                    \ufeff
                    <span
                        class="something"
                        contenteditable
                        style='font-size: 5px; font-family:"Helvetica Neue";'
                        data-attr="console.log('it works')"
                    />
                    def ghi
                    <br><br>
                </div>
                <p>jkl</p>
                <div class="hello"/>
                <fake-node fake="true"
                    style='font-size: 5px; font-family:"Helvetica Neue";'>
                    <div>mno</div>
                    <p><span>pqr</span>
                        stu<b>
                            vwx
                        </b>
                    </p>
                </fake-node>
            `)
        ).toBe(
            `<div>` +
                `abc
                    \ufeff` +
                `<span ` +
                `class="something" ` +
                `contenteditable ` +
                `style='font-size: 5px; font-family:"Helvetica Neue";' ` +
                `data-attr="console.log('it works')"` +
                `/>` +
                `def ghi` +
                `<br><br>` +
                `</div>` +
                `<p>jkl</p>` +
                `<div class="hello"/>` +
                `<fake-node fake="true" ` +
                `style='font-size: 5px; font-family:"Helvetica Neue";'>` +
                `<div>mno</div>` +
                `<p><span>pqr</span>` +
                `stu<b>` +
                `vwx` +
                `</b>` +
                `</p>` +
                `</fake-node>`
        );
    });
});
