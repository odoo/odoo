import { test } from "@odoo/hoot";
import { testEditor } from "./_helpers/editor";
import { unformat } from "./_helpers/format";
import { setColor } from "./_helpers/user_actions";

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
        contentAfter: "<p>[</p><p></p><p>]</p>",
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
        contentAfter: "<p>[</p><p></p><p>]</p>",
    });
});

test("should not merge line on background color change", async () => {
    await testEditor({
        contentBefore: "<p><strong>[abcd</strong><br><strong>efghi]</strong></p>",
        stepFunction: setColor("rgb(255, 0, 0)", "backgroundColor"),
        contentAfter:
            '<p><strong><font style="background-color: rgb(255, 0, 0);">[abcd</font></strong><br>' +
            '<strong><font style="background-color: rgb(255, 0, 0);">efghi]</font></strong></p>',
    });
});

test("should not merge line on color change", async () => {
    await testEditor({
        contentBefore: "<p><strong>[abcd</strong><br><strong>efghi]</strong></p>",
        stepFunction: setColor("rgb(255, 0, 0)", "color"),
        contentAfter:
            '<p><strong><font style="color: rgb(255, 0, 0);">[abcd</font></strong><br>' +
            '<strong><font style="color: rgb(255, 0, 0);">efghi]</font></strong></p>',
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
                        <font style="color: red;">AzureInterior</font>
                    </t>
                </t>
                <t t-else="">
                    <t t-out="object.partner_id.name or ''" style="color: red;">
                        <font style="color: red;">BrandonFreeman</font>
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
        contentBefore: '<p>a[b<a class="btn">c</a>d]e</p>',
        stepFunction: setColor("rgb(255, 0, 0)", "color"),
        contentAfter:
            '<p>a<font style="color: rgb(255, 0, 0);">[b</font>' +
            '<a class="btn"><font style="color: rgb(255, 0, 0);">c</font></a>' +
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
            '<p><font class="text-gradient" style="background-image: linear-gradient(135deg, rgb(214, 255, 127) 0%, rgb(0, 179, 204) 100%);">ab<font style="background-color: rgb(255, 0, 0);">[ca]</font>bc</font></p>',
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
