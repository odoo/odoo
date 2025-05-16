import { after, before, describe, expect, test } from "@odoo/hoot";
import { setupEditor, testEditor } from "./_helpers/editor";
import { unformat } from "./_helpers/format";
import { setColor } from "./_helpers/user_actions";
import { getContent } from "./_helpers/selection";

const redToBlueGradient = "linear-gradient(rgb(255, 0, 0), rgb(0, 0, 255))";
const greenToBlueGradient = "linear-gradient(rgb(0, 255, 0), rgb(0, 0, 255))";

test("should apply a color to a slice of text in a span in a font", async () => {
    await testEditor({
        contentBefore: '<p>a<font class="a">b<span class="b">c[def]g</span>h</font>i</p>',
        stepFunction: setColor("rgb(255, 0, 0)", "color"),
        contentAfter:
            '<p>a<font class="a">b<span class="b">c</span></font>' +
            '<font class="a" style="color: rgb(255, 0, 0);"><span class="b">[def]</span></font>' +
            '<font class="a"><span class="b">g</span>h</font>i</p>',
    });
});

test("should apply a color to the qweb tag", async () => {
    await testEditor({
        contentBefore: `<div><p t-esc="'Test'" contenteditable="false">[Test]</p></div>`,
        stepFunction: setColor("rgb(255, 0, 0)", "color"),
        contentAfter: `<div>[<p t-esc="'Test'" contenteditable="false" style="color: rgb(255, 0, 0);">Test</p>]</div>`,
    });

    await testEditor({
        contentBefore: `<div><p t-field="record.display_name" contenteditable="false">[Test]</p></div>`,
        stepFunction: setColor("rgb(255, 0, 0)", "color"),
        contentAfter: `<div>[<p t-field="record.display_name" contenteditable="false" style="color: rgb(255, 0, 0);">Test</p>]</div>`,
    });
});

test("should apply a background color to a slice of text in a span in a font", async () => {
    await testEditor({
        contentBefore: '<p>a<font class="a">b<span class="b">c[def]g</span>h</font>i</p>',
        stepFunction: setColor("rgb(255, 0, 0)", "backgroundColor"),
        contentAfter:
            '<p>a<font class="a">b<span class="b">c</span></font>' +
            '<font class="a" style="background-color: rgb(255, 0, 0);"><span class="b">[def]</span></font>' +
            '<font class="a"><span class="b">g</span>h</font>i</p>',
    });
});

test("should get ready to type with a different color", async () => {
    await testEditor({
        contentBefore: "<p>ab[]cd</p>",
        stepFunction: setColor("rgb(255, 0, 0)", "color"),
        contentAfter: '<p>ab<font style="color: rgb(255, 0, 0);">[]\u200B</font>cd</p>',
    });
});

test("should get ready to type with a different background color", async () => {
    await testEditor({
        contentBefore: "<p>ab[]cd</p>",
        stepFunction: setColor("rgb(255, 0, 0)", "backgroundColor"),
        contentAfter: '<p>ab<font style="background-color: rgb(255, 0, 0);">[]\u200B</font>cd</p>',
    });
});

test("should apply a color on empty selection", async () => {
    await testEditor({
        contentBefore: "<p>[<br></p><p><br></p><p>]<br></p>",
        stepFunction: setColor("rgb(255, 0, 0)", "color"),
        contentAfterEdit:
            '<p>[<font data-oe-zws-empty-inline="" style="color: rgb(255, 0, 0);">\u200B</font></p>' +
            '<p><font data-oe-zws-empty-inline="" style="color: rgb(255, 0, 0);">\u200B</font></p>' +
            '<p>]<font data-oe-zws-empty-inline="" style="color: rgb(255, 0, 0);">\u200B</font></p>',
        contentAfter: "<p>[<br></p><p><br></p><p>]<br></p>",
    });
});

test("should apply a background color on empty selection", async () => {
    await testEditor({
        contentBefore: "<p>[<br></p><p><br></p><p>]<br></p>",
        stepFunction: setColor("rgb(255, 0, 0)", "backgroundColor"),
        contentAfterEdit:
            '<p>[<font data-oe-zws-empty-inline="" style="background-color: rgb(255, 0, 0);">\u200B</font></p>' +
            '<p><font data-oe-zws-empty-inline="" style="background-color: rgb(255, 0, 0);">\u200B</font></p>' +
            '<p>]<font data-oe-zws-empty-inline="" style="background-color: rgb(255, 0, 0);">\u200B</font></p>',
        contentAfter: "<p>[<br></p><p><br></p><p>]<br></p>",
    });
});

test("should not merge line on background color change", async () => {
    await testEditor({
        contentBefore: "<p><strong>[abcd</strong><br><strong>efghi]</strong></p>",
        stepFunction: setColor("rgb(255, 0, 0)", "backgroundColor"),
        contentAfter:
            '<p><font style="background-color: rgb(255, 0, 0);"><strong>[abcd</strong></font><br>' +
            '<font style="background-color: rgb(255, 0, 0);"><strong>efghi]</strong></font></p>',
    });
});

test("should not merge line on color change", async () => {
    await testEditor({
        contentBefore: "<p><strong>[abcd</strong><br><strong>efghi]</strong></p>",
        stepFunction: setColor("rgb(255, 0, 0)", "color"),
        contentAfter:
            '<p><font style="color: rgb(255, 0, 0);"><strong>[abcd</strong></font><br>' +
            '<font style="color: rgb(255, 0, 0);"><strong>efghi]</strong></font></p>',
    });
});

test("should not apply color on an uneditable element", async () => {
    await testEditor({
        contentBefore: '<p>[a</p><p contenteditable="false">b</p><p>c]</p>',
        stepFunction: setColor("rgb(255, 0, 0)", "color"),
        contentAfter: unformat(`
                <p><font style="color: rgb(255, 0, 0);">[a</font></p>
                <p contenteditable="false">b</p>
                <p><font style="color: rgb(255, 0, 0);">c]</font></p>
            `),
    });
});

test("should apply color with default text color on block when applying background color", async () => {
    const defaultTextColor = "color: rgb(1, 10, 100);";
    const styleContent = `* {${defaultTextColor}}`;
    await testEditor({
        contentBefore: unformat(`
                <table><tbody>
                    <tr><td class="o_selected_td">[ab</td></tr>
                    <tr><td class="o_selected_td">cd]</td></tr>
                </tbody></table>
            `),
        stepFunction: setColor("rgb(255, 0, 0)", "backgroundColor"),
        contentAfter: unformat(`
                <table><tbody>
                    <tr><td style="background-color: rgb(255, 0, 0); ${defaultTextColor}">[ab</td></tr>
                    <tr><td style="background-color: rgb(255, 0, 0); ${defaultTextColor}">cd]</td></tr>
                </tbody></table>
            `),
        styleContent,
    });
});

test("should remove color from block when removing background color", async () => {
    const defaultTextColor = "color: rgb(1, 10, 100);";
    const styleContent = `* {${defaultTextColor}}`;
    await testEditor({
        contentBefore: unformat(`
            <table><tbody>
                <tr><td style="background-color: rgb(255, 0, 0); ${defaultTextColor}">[ab</td></tr>
                <tr><td style="background-color: rgb(255, 0, 0); ${defaultTextColor}">cd]</td></tr>
            </tbody></table>
        `),
        stepFunction: setColor("", "backgroundColor"),
        contentAfter: unformat(`
            <table><tbody>
                <tr><td>[ab</td></tr>
                <tr><td>cd]</td></tr>
            </tbody></table>
        `),
        styleContent,
    });
});

test("should not apply background color on an uneditable selected cell in a table", async () => {
    const defaultTextColor = "color: rgb(1, 10, 100);";
    const styleContent = `* {${defaultTextColor};}`;
    await testEditor({
        contentBefore: unformat(`
                <table><tbody>
                    <tr><td class="o_selected_td">[ab</td></tr>
                    <tr><td contenteditable="false" class="o_selected_td">cd</td></tr>
                    <tr><td class="o_selected_td">ef]</td></tr>
                </tbody></table>
            `),
        stepFunction: setColor("rgb(255, 0, 0)", "backgroundColor"),
        contentAfter: unformat(`
                <table><tbody>
                    <tr><td style="background-color: rgb(255, 0, 0); ${defaultTextColor}">[ab</td></tr>
                    <tr><td contenteditable="false">cd</td></tr>
                    <tr><td style="background-color: rgb(255, 0, 0); ${defaultTextColor}">ef]</td></tr>
                </tbody></table>
            `),
        styleContent,
    });
});

test("should not apply font tag to t nodes (protects if else nodes separation)", async () => {
    await testEditor({
        contentBefore: unformat(`[
            <p>
                <t t-if="object.partner_id.parent_id">
                   <t t-out="object.partner_id.parent_id.name or ''">Azure Interior</t>
                </t>
                <t t-else="">
                    <t t-out="object.partner_id.name or ''">Brandon Freeman</t>
                </t>
            </p>
        ]`),
        stepFunction: setColor("red", "color"),
        contentAfter: unformat(`[
            <p>
                <t t-if="object.partner_id.parent_id">
                    <t t-out="object.partner_id.parent_id.name or ''" style="color: red;">
                        <font style="color: red;">Azure Interior</font>
                    </t>
                </t>
                <t t-else="">
                    <t t-out="object.partner_id.name or ''" style="color: red;">
                        <font style="color: red;">Brandon Freeman</font>
                    </t>
                </t>
            </p>
        ]`),
    });
});

test("should remove font tag after removing font color", async () => {
    await testEditor({
        contentBefore: '<p><font style="color: rgb(255, 0, 0);">[abcabc]</font></p>',
        stepFunction: setColor("", "color"),
        contentAfter: "<p>[abcabc]</p>",
    });
    await testEditor({
        contentBefore: '<p><font class="text-400">[abcabc]</font></p>',
        stepFunction: setColor("", "color"),
        contentAfter: "<p>[abcabc]</p>",
    });
});

test("should remove font tag after removing background color applied as style", async () => {
    await testEditor({
        contentBefore: '<p><font style="background-color: rgb(255, 0, 0);">[abcabc]</font></p>',
        stepFunction: setColor("", "backgroundColor"),
        contentAfter: "<p>[abcabc]</p>",
    });
    await testEditor({
        contentBefore: '<p><font class="bg-200">[abcabc]</font></p>',
        stepFunction: setColor("", "backgroundColor"),
        contentAfter: "<p>[abcabc]</p>",
    });
});

test("should remove font tag if font-color and background-color both are removed one by one", async () => {
    await testEditor({
        contentBefore: '<p><font style="color: rgb(255, 0, 0);" class="bg-200">[abcabc]</font></p>',
        stepFunction: (editor) => {
            setColor("", "backgroundColor")(editor);
            setColor("", "color")(editor);
        },
        contentAfter: "<p>[abcabc]</p>",
    });
    await testEditor({
        contentBefore:
            '<p><font style="background-color: rgb(255, 0, 0);" class="text-900">[abcabc]</font></p>',
        stepFunction: (editor) => {
            setColor("", "color")(editor);
            setColor("", "backgroundColor")(editor);
        },
        contentAfter: "<p>[abcabc]</p>",
    });
});

test("should apply a color to a slice of text containing a span", async () => {
    await testEditor({
        contentBefore: '<p>a[b<span class="a">c</span>d]e</p>',
        stepFunction: setColor("rgb(255, 0, 0)", "color"),
        contentAfter:
            '<p>a<font style="color: rgb(255, 0, 0);">[b<span class="a">c</span>d]</font>e</p>',
    });
});

test("should apply background color to a list of 3 items with font size", async () => {
    await testEditor({
        contentBefore:
            "<ul>" +
            "<li>" +
            '<span style="font-size: 36px;">' +
            "[abc" +
            "</span>" +
            "</li>" +
            "<li>" +
            '<span style="font-size: 36px;">' +
            "bcd" +
            "</span>" +
            "</li>" +
            "<li>" +
            '<span style="font-size: 36px;">' +
            "cde]" +
            "</span>" +
            "</li>" +
            "</ul>",
        stepFunction: setColor("rgb(255, 0, 0)", "backgroundColor"),

        contentAfter:
            "<ul>" +
            "<li>" +
            '<span style="font-size: 36px;">' +
            '<font style="background-color: rgb(255, 0, 0);">' +
            "[abc" +
            "</font>" +
            "</span>" +
            "</li>" +
            "<li>" +
            '<span style="font-size: 36px;">' +
            '<font style="background-color: rgb(255, 0, 0);">' +
            "bcd" +
            "</font>" +
            "</span>" +
            "</li>" +
            "<li>" +
            '<span style="font-size: 36px;">' +
            '<font style="background-color: rgb(255, 0, 0);">' +
            "cde]" +
            "</font>" +
            "</span>" +
            "</li>" +
            "</ul>",
    });
});

test("should apply background color to a list of 3 links", async () => {
    await testEditor({
        contentBefore:
            "<ul>" +
            "<li>" +
            '<a href="#">' +
            "[abc" +
            "</a>" +
            "</li>" +
            "<li>" +
            '<a href="#">' +
            "bcd" +
            "</a>" +
            "</li>" +
            "<li>" +
            '<a href="#">' +
            "cde]" +
            "</a>" +
            "</li>" +
            "</ul>",
        stepFunction: setColor("rgb(255, 0, 0)", "backgroundColor"),
        contentAfter:
            "<ul>" +
            "<li>" +
            '<a href="#">' +
            '<font style="background-color: rgb(255, 0, 0);">' +
            "[abc" +
            "</font>" +
            "</a>" +
            "</li>" +
            "<li>" +
            '<a href="#">' +
            '<font style="background-color: rgb(255, 0, 0);">' +
            "bcd" +
            "</font>" +
            "</a>" +
            "</li>" +
            "<li>" +
            '<a href="#">' +
            '<font style="background-color: rgb(255, 0, 0);">' +
            "cde]" +
            "</font>" +
            "</a>" +
            "</li>" +
            "</ul>",
    });
});

test("should distribute color to texts and to button separately", async () => {
    await testEditor({
        contentBefore: '<p>a[b<a href="#" class="btn">c</a>d]e</p>',
        stepFunction: setColor("rgb(255, 0, 0)", "color"),
        contentAfter:
            '<p>a<font style="color: rgb(255, 0, 0);">[b</font>' +
            '<a href="#" class="btn"><font style="color: rgb(255, 0, 0);">c</font></a>' +
            '<font style="color: rgb(255, 0, 0);">d]</font>e</p>',
    });
});

test("should apply text color whithout interrupting gradient background color on selected text", async () => {
    await testEditor({
        contentBefore:
            '<p><font style="background-image: linear-gradient(135deg, rgb(214, 255, 127) 0%, rgb(0, 179, 204) 100%);">ab[ca]bc</font></p>',
        stepFunction: setColor("rgb(255, 0, 0)", "color"),
        contentAfter:
            '<p><font style="background-image: linear-gradient(135deg, rgb(214, 255, 127) 0%, rgb(0, 179, 204) 100%);">ab<font style="color: rgb(255, 0, 0);">[ca]</font>bc</font></p>',
    });
});
test("should apply background color whithout interrupting gradient text color on selected text", async () => {
    await testEditor({
        contentBefore:
            '<p><font class="text-gradient" style="background-image: linear-gradient(135deg, rgb(214, 255, 127) 0%, rgb(0, 179, 204) 100%);">ab[ca]bc</font></p>',
        stepFunction: setColor("rgb(255, 0, 0)", "backgroundColor"),
        contentAfter:
            '<p><font class="text-gradient" style="background-image: linear-gradient(135deg, rgb(214, 255, 127) 0%, rgb(0, 179, 204) 100%);">ab<font style="background-image: none; background-color: rgb(255, 0, 0);">[ca]</font>bc</font></p>',
    });
});
test("should apply background color whithout interrupting gradient background color on selected text", async () => {
    await testEditor({
        contentBefore:
            '<p><font style="background-image: linear-gradient(135deg, rgb(214, 255, 127) 0%, rgb(0, 179, 204) 100%);">ab[ca]bc</font></p>',
        stepFunction: setColor("rgb(255, 0, 0)", "backgroundColor"),
        contentAfter:
            '<p><font style="background-image: linear-gradient(135deg, rgb(214, 255, 127) 0%, rgb(0, 179, 204) 100%);">ab<font style="background-color: rgb(255, 0, 0);">[ca]</font>bc</font></p>',
    });
});
test("should apply text color whithout interrupting gradient text color on selected text", async () => {
    await testEditor({
        contentBefore:
            '<p><font class="text-gradient" style="background-image: linear-gradient(135deg, rgb(214, 255, 127) 0%, rgb(0, 179, 204) 100%);">ab[ca]bc</font></p>',
        stepFunction: setColor("rgb(255, 0, 0)", "color"),
        contentAfter:
            '<p><font class="text-gradient" style="background-image: linear-gradient(135deg, rgb(214, 255, 127) 0%, rgb(0, 179, 204) 100%);">ab<font style="-webkit-text-fill-color: rgb(255, 0, 0); color: rgb(255, 0, 0);">[ca]</font>bc</font></p>',
    });
});
test("should break gradient color on selected text", async () => {
    await testEditor({
        contentBefore:
            '<p><font class="text-gradient" style="background-image: linear-gradient(135deg, rgb(214, 255, 127) 0%, rgb(0, 179, 204) 100%);">ab[ca]bc</font></p>',
        stepFunction: setColor(
            "linear-gradient(135deg, rgb(255, 174, 127) 0%, rgb(109, 204, 0) 100%)",
            "backgroundColor"
        ),
        contentAfter:
            '<p><font class="text-gradient" style="background-image: linear-gradient(135deg, rgb(214, 255, 127) 0%, rgb(0, 179, 204) 100%);">ab</font>' +
            '<font style="background-image: linear-gradient(135deg, rgb(255, 174, 127) 0%, rgb(109, 204, 0) 100%);">[ca]</font>' +
            '<font class="text-gradient" style="background-image: linear-gradient(135deg, rgb(214, 255, 127) 0%, rgb(0, 179, 204) 100%);">bc</font></p>',
    });
});
test("should update the gradient color and remove the nested background color to make the gradient visible", async () => {
    await testEditor({
        contentBefore:
            '<p><font style="background-image: linear-gradient(135deg, rgb(214, 255, 127) 0%, rgb(0, 179, 204) 100%);"><font style="background-color: rgb(255, 0, 0);">[abc]</font></font></p>',
        stepFunction: setColor(
            "linear-gradient(135deg, rgb(255, 174, 127) 0%, rgb(109, 204, 0) 100%)",
            "backgroundColor"
        ),
        contentAfter:
            '<p><font style="background-image: linear-gradient(135deg, rgb(255, 174, 127) 0%, rgb(109, 204, 0) 100%);">[abc]</font></p>',
    });
});
test("should update the gradient text color and remove the nested text color to make the gradient visible", async () => {
    await testEditor({
        contentBefore:
            '<p><font class="text-gradient" style="background-image: linear-gradient(135deg, rgb(214, 255, 127) 0%, rgb(0, 179, 204) 100%);"><font style="-webkit-text-fill-color: rgb(255, 0, 0); color: rgb(255, 0, 0);">[abc]</font></font></p>',
        stepFunction: setColor(
            "linear-gradient(135deg, rgb(255, 174, 127) 0%, rgb(109, 204, 0) 100%)",
            "color"
        ),
        contentAfter:
            '<p><font class="text-gradient" style="background-image: linear-gradient(135deg, rgb(255, 174, 127) 0%, rgb(109, 204, 0) 100%);">[abc]</font></p>',
    });
});
test("should apply gradient color when a when background color is applied on span", async () => {
    await testEditor({
        contentBefore: '<p><span style="background-color: rgb(255, 0, 0)">ab[ca]bc</span></p>',
        stepFunction: setColor(
            "linear-gradient(135deg, rgb(255, 174, 127) 0%, rgb(109, 204, 0) 100%)",
            "color"
        ),
        contentAfter:
            '<p><span style="background-color: rgb(255, 0, 0)">ab<font class="text-gradient" style="background-image: linear-gradient(135deg, rgb(255, 174, 127) 0%, rgb(109, 204, 0) 100%);">[ca]</font>bc</span></p>',
    });
});
test("should apply a gradient color to a slice of text in a span", async () => {
    await testEditor({
        contentBefore: '<p><span class="a">ab[ca]bc</span></p>',
        stepFunction: setColor(
            "linear-gradient(135deg, rgb(255, 174, 127) 0%, rgb(109, 204, 0) 100%)",
            "color"
        ),
        contentAfter:
            '<p><span class="a">ab<font class="text-gradient" style="background-image: linear-gradient(135deg, rgb(255, 174, 127) 0%, rgb(109, 204, 0) 100%);">[ca]</font>bc</span></p>',
    });
});
test("should applied background color to slice of text in a span without interrupting gradient background color", async () => {
    await testEditor({
        contentBefore:
            '<p><font style="background-image: linear-gradient(135deg, rgb(214, 255, 127) 0%, rgb(0, 179, 204) 100%);"><span class="a">ab[ca]bc</span></font></p>',
        stepFunction: setColor("rgb(255, 0, 0)", "backgroundColor"),
        contentAfter:
            '<p><font style="background-image: linear-gradient(135deg, rgb(214, 255, 127) 0%, rgb(0, 179, 204) 100%);"><span class="a">ab<font style="background-color: rgb(255, 0, 0);">[ca]</font>bc</span></font></p>',
    });
});
test("should break a gradient and apply gradient background color to a slice of text within a span", async () => {
    await testEditor({
        contentBefore:
            '<p><font style="background-image: linear-gradient(135deg, rgb(214, 255, 127) 0%, rgb(0, 179, 204) 100%);"><span class="a">ab<font style="background-color: rgb(255, 0, 0);">[ca]</font>bc</span></font></p>',
        stepFunction: setColor(
            "linear-gradient(135deg, rgb(255, 174, 127) 0%, rgb(109, 204, 0) 100%)",
            "color"
        ),
        contentAfter:
            '<p><font style="background-image: linear-gradient(135deg, rgb(214, 255, 127) 0%, rgb(0, 179, 204) 100%);"><span class="a">ab</span></font>' +
            '<font style="background-image: linear-gradient(135deg, rgb(255, 174, 127) 0%, rgb(109, 204, 0) 100%);" class="text-gradient"><span class="a"><font style="background-color: rgb(255, 0, 0);">[ca]</font></span></font>' +
            '<font style="background-image: linear-gradient(135deg, rgb(214, 255, 127) 0%, rgb(0, 179, 204) 100%);"><span class="a">bc</span></font></p>',
    });
});
test("should apply gradient color on selected text", async () => {
    await testEditor({
        contentBefore: '<div style="background-image:none"><p>[ab<strong>cd</strong>ef]</p></div>',
        stepFunction: setColor(
            "linear-gradient(135deg, rgb(255, 174, 127) 0%, rgb(109, 204, 0) 100%)",
            "backgroundColor"
        ),
        contentAfter:
            '<div style="background-image:none"><p><font style="background-image: linear-gradient(135deg, rgb(255, 174, 127) 0%, rgb(109, 204, 0) 100%);">[ab<strong>cd</strong>ef]</font></p></div>',
    });
});
test("should apply gradient text color on selected text", async () => {
    await testEditor({
        contentBefore: '<div style="background-image:none"><p>[ab<strong>cd</strong>ef]</p></div>',
        stepFunction: setColor(
            "linear-gradient(135deg, rgb(255, 174, 127) 0%, rgb(109, 204, 0) 100%)",
            "color"
        ),
        contentAfter:
            '<div style="background-image:none"><p><font class="text-gradient" style="background-image: linear-gradient(135deg, rgb(255, 174, 127) 0%, rgb(109, 204, 0) 100%);">[ab<strong>cd</strong>ef]</font></p></div>',
    });
});

test("should merge adjacent font with the same text color when mutations common root is <font>", async () => {
    // This test should not execute clean for save as the bug will no longer exists
    const { el, editor } = await setupEditor(
        '<p><font style="color: rgb(255, 0, 0);">first </font><font style="color: rgb(0, 255, 0);">[second]</font></p>'
    );
    await setColor("rgb(255, 0, 0)", "color")(editor);
    const expected = '<p><font style="color: rgb(255, 0, 0);">first [second]</font></p>';
    expect(getContent(el)).toBe(expected);
});

test("should keep font element on top of underline/strike (1)", async () => {
    await testEditor({
        contentBefore: "<p><u>[abc]</u></p>",
        stepFunction: setColor(
            "linear-gradient(135deg, rgb(255, 174, 127) 0%, rgb(109, 204, 0) 100%)",
            "color"
        ),
        contentAfter:
            '<p><font class="text-gradient" style="background-image: linear-gradient(135deg, rgb(255, 174, 127) 0%, rgb(109, 204, 0) 100%);"><u>[abc]</u></font></p>',
    });
});

test("should keep font element on top of underline/strike (2)", async () => {
    await testEditor({
        contentBefore: "<p><u><s>[abc]</s></u></p>",
        stepFunction: setColor(
            "linear-gradient(135deg, rgb(255, 174, 127) 0%, rgb(109, 204, 0) 100%)",
            "color"
        ),
        contentAfter:
            '<p><font class="text-gradient" style="background-image: linear-gradient(135deg, rgb(255, 174, 127) 0%, rgb(109, 204, 0) 100%);"><u><s>[abc]</s></u></font></p>',
    });
});

describe("colorElement", () => {
    test("should apply o_cc1 class to the element when a color wasn't defined", async () => {
        await testEditor({
            contentBefore: "<div>a</div>",
            stepFunction: (editor) => {
                editor.shared.color.colorElement(
                    editor.editable.firstChild,
                    "o_cc1",
                    "backgroundColor"
                );
            },
            contentAfter: '<div class="o_cc o_cc1">a</div>',
        });
    });
    describe("when a color was defined", () => {
        test("should apply o_cc1 class to the element when a color #ff0000 was defined", async () => {
            await testEditor({
                contentBefore: `<div style="background-color: #ff0000;">a</div>`,
                stepFunction: (editor) => {
                    editor.shared.color.colorElement(
                        editor.editable.firstChild,
                        "o_cc1",
                        "backgroundColor"
                    );
                },
                contentAfter: '<div style="background-color: #ff0000;" class="o_cc o_cc1">a</div>',
            });
        });
        test("should apply o_cc1 class to the element when a color bg-900 was defined", async () => {
            await testEditor({
                contentBefore: `<div class="bg-900">a</div>`,
                stepFunction: (editor) => {
                    editor.shared.color.colorElement(
                        editor.editable.firstChild,
                        "o_cc1",
                        "backgroundColor"
                    );
                },
                contentAfter: '<div class="bg-900 o_cc o_cc1">a</div>',
            });
        });
        test("should apply o_cc1 class to the element when a color gradient was defined", async () => {
            await testEditor({
                contentBefore: `<div style="background-image: ${greenToBlueGradient};">a</div>`,
                stepFunction: (editor) => {
                    editor.shared.color.colorElement(
                        editor.editable.firstChild,
                        "o_cc1",
                        "backgroundColor"
                    );
                },
                contentAfter: `<div style="background-image: ${greenToBlueGradient};" class="o_cc o_cc1">a</div>`,
            });
        });
    });

    test("should keep o_cc1 when adding a color", async () => {
        await testEditor({
            contentBefore: `<div class="o_cc o_cc1">a</div>`,
            stepFunction: (editor) => {
                editor.shared.color.colorElement(
                    editor.editable.firstChild,
                    "rgb(255, 0, 0)",
                    "backgroundColor"
                );
            },
            contentAfter:
                '<div class="o_cc o_cc1" style="background-color: rgb(255, 0, 0);">a</div>',
        });
    });

    test("should keep the background image when applying a gradient", async () => {
        await testEditor({
            contentBefore: `<div style='background-image: url("https://example.com/image.png");'>a</div>`,
            stepFunction: (editor) => {
                editor.shared.color.colorElement(
                    editor.editable.firstChild,
                    greenToBlueGradient,
                    "backgroundColor"
                );
            },
            contentAfter: `<div style='background-image: url("https://example.com/image.png"), ${greenToBlueGradient};'>a</div>`,
        });
    });
    test("should keep custom gradient when switching o_cc class", async () => {
        await testEditor({
            contentBefore: `<div class="">a</div>`,
            stepFunction: (editor) => {
                editor.shared.color.colorElement(
                    editor.editable.firstChild,
                    "o_cc1",
                    "backgroundColor"
                );
                editor.shared.color.colorElement(
                    editor.editable.firstChild,
                    greenToBlueGradient,
                    "backgroundColor"
                );
                editor.shared.color.colorElement(
                    editor.editable.firstChild,
                    "o_cc2",
                    "backgroundColor"
                );
            },
            contentAfter: `<div class="o_cc o_cc2" style="background-image: ${greenToBlueGradient};">a</div>`,
        });
    });

    describe("with o_cc1 gradient defined", () => {
        before(() => {
            const styleElement = document.createElement("style");
            styleElement.id = "temp-test-style";
            styleElement.textContent = `.o_cc1 {
    background-image: ${redToBlueGradient};
}`;
            document.head.appendChild(styleElement);
            after(() => {
                styleElement.remove();
            });
        });
        test("should remove o_cc1 when setting an empty color", async () => {
            await testEditor({
                contentBefore: `<div class="o_cc o_cc1" style="background-image: ${redToBlueGradient};">a</div>`,
                stepFunction: (editor) => {
                    editor.shared.color.colorElement(
                        editor.editable.firstChild,
                        "",
                        "backgroundColor"
                    );
                },
                contentAfter: `<div>a</div>`,
            });
        });
        test("should write background-image gradient when o_cc1 has a gradient", async () => {
            await testEditor({
                contentBefore: `<div>a</div>`,
                stepFunction: (editor) => {
                    editor.shared.color.colorElement(
                        editor.editable.firstChild,
                        "o_cc1",
                        "backgroundColor"
                    );
                },
                contentAfter: `<div class="o_cc o_cc1" style="background-image: ${redToBlueGradient};">a</div>`,
            });
        });
        test("should keep the background image when applying o_cc1 gradient", async () => {
            await testEditor({
                contentBefore: `<div style='background-image: url("https://example.com/image.png");'>a</div>`,
                stepFunction: (editor) => {
                    editor.shared.color.colorElement(
                        editor.editable.firstChild,
                        "o_cc1",
                        "backgroundColor"
                    );
                },
                contentAfter: `<div style='background-image: url("https://example.com/image.png"), ${redToBlueGradient};' class="o_cc o_cc1">a</div>`,
            });
        });
        test("change o_cc1 (with gradient) with o_cc2 (without gradient)", async () => {
            await testEditor({
                contentBefore: `<div class="o_cc1" style="background-image: ${redToBlueGradient};">a</div>`,
                stepFunction: (editor) => {
                    editor.shared.color.colorElement(
                        editor.editable.firstChild,
                        "o_cc2",
                        "backgroundColor"
                    );
                },
                contentAfter: `<div class="o_cc o_cc2">a</div>`,
            });
        });

        describe("set o_cc1 when a color is already defined", () => {
            test("should not write o_cc1 gradient when rgb(255, 0, 0) is already present", async () => {
                await testEditor({
                    contentBefore: `<div style="background-color: rgb(255, 0, 0);">a</div>`,
                    stepFunction: (editor) => {
                        editor.shared.color.colorElement(
                            editor.editable.firstChild,
                            "o_cc1",
                            "backgroundColor"
                        );
                    },
                    contentAfter: `<div style="background-color: rgb(255, 0, 0); background-image: none;" class="o_cc o_cc1">a</div>`,
                });
            });
            test("should not write o_cc1 gradient when bg-900 is already present", async () => {
                await testEditor({
                    contentBefore: `<div class="bg-900">a</div>`,
                    stepFunction: (editor) => {
                        editor.shared.color.colorElement(
                            editor.editable.firstChild,
                            "o_cc1",
                            "backgroundColor"
                        );
                    },
                    contentAfter: `<div class="bg-900 o_cc o_cc1" style="background-image: none;">a</div>`,
                });
            });
            test("should not write o_cc1 gradient when a gradient is already present", async () => {
                await testEditor({
                    contentBefore: `<div style="background-image: ${greenToBlueGradient};">a</div>`,
                    stepFunction: (editor) => {
                        editor.shared.color.colorElement(
                            editor.editable.firstChild,
                            "o_cc1",
                            "backgroundColor"
                        );
                    },
                    contentAfter: `<div style="background-image: ${greenToBlueGradient};" class="o_cc o_cc1">a</div>`,
                });
            });
        });
        describe("set a color when a o_cc1 is already defined", () => {
            test("should not have an o_cc1 gradient when applying the color rgb(255, 0, 0)", async () => {
                await testEditor({
                    contentBefore: `<div class="o_cc o_cc1">a</div>`,
                    stepFunction: (editor) => {
                        editor.shared.color.colorElement(
                            editor.editable.firstChild,
                            "rgb(255, 0, 0)",
                            "backgroundColor"
                        );
                    },
                    contentAfter:
                        '<div class="o_cc o_cc1" style="background-image: none; background-color: rgb(255, 0, 0);">a</div>',
                });
            });
            test("should not have an o_cc1 gradient when applying the color bg-900", async () => {
                await testEditor({
                    contentBefore: `<div class="o_cc o_cc1">a</div>`,
                    stepFunction: (editor) => {
                        editor.shared.color.colorElement(
                            editor.editable.firstChild,
                            "bg-900",
                            "backgroundColor"
                        );
                    },
                    contentAfter:
                        '<div class="o_cc o_cc1 bg-900" style="background-image: none;">a</div>',
                });
            });
            test("should not have an o_cc1 gradient when applying a gradient color", async () => {
                await testEditor({
                    contentBefore: `<div class="o_cc o_cc1">a</div>`,
                    stepFunction: (editor) => {
                        editor.shared.color.colorElement(
                            editor.editable.firstChild,
                            greenToBlueGradient,
                            "backgroundColor"
                        );
                    },
                    contentAfter: `<div class="o_cc o_cc1" style="background-image: ${greenToBlueGradient};">a</div>`,
                });
            });
        });
    });
});
