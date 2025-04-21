/** @odoo-module */

import { BasicEditor, testEditor, unformat } from '../utils.js';
import { rgbToHex } from '../../src/utils/utils.js';

const setColor = (color, mode) => {
    return async editor => {
        await editor.execCommand('applyColor', color, mode);
    };
};

describe('applyColor', () => {
    it('should apply a color to a slice of text in a span in a font', async () => {
        await testEditor(BasicEditor, {
            contentBefore: '<p>a<font class="a">b<span class="b">c[def]g</span>h</font>i</p>',
            stepFunction: setColor('rgb(255, 0, 0)', 'color'),
            contentAfter: '<p>a<font class="a">b<span class="b">c</span></font>' +
                '<font class="a" style="color: rgb(255, 0, 0);"><span class="b">[def]</span></font>' +
                '<font class="a"><span class="b">g</span>h</font>i</p>',
        });
    });
    it('should apply a color to the qweb tag', async () => {
        await testEditor(BasicEditor, {
            contentBefore: `<div><p t-esc="'Test'" contenteditable="false">[Test]</p></div>`,
            stepFunction: setColor('rgb(255, 0, 0)', 'color'),
            contentAfter: `<div>[<p t-esc="'Test'" contenteditable="false" style="color: rgb(255, 0, 0);">Test</p>]</div>`,
        });

        await testEditor(BasicEditor, {
            contentBefore: `<div><p t-field="record.display_name" contenteditable="false">[Test]</p></div>`,
            stepFunction: setColor('rgb(255, 0, 0)', 'color'),
            contentAfter: `<div>[<p t-field="record.display_name" contenteditable="false" style="color: rgb(255, 0, 0);">Test</p>]</div>`,
        });
    });
    it('should apply a background color to a slice of text in a span in a font', async () => {
        await testEditor(BasicEditor, {
            contentBefore: '<p>a<font class="a">b<span class="b">c[def]g</span>h</font>i</p>',
            stepFunction: setColor('rgb(255, 0, 0)', 'backgroundColor'),
            contentAfter: '<p>a<font class="a">b<span class="b">c</span></font>' +
                '<font class="a" style="background-color: rgb(255, 0, 0);"><span class="b">[def]</span></font>' +
                '<font class="a"><span class="b">g</span>h</font>i</p>',
        });
    });
    it('should get ready to type with a different color', async () => {
        await testEditor(BasicEditor, {
            contentBefore: '<p>ab[]cd</p>',
            stepFunction: setColor('rgb(255, 0, 0)', 'color'),
            contentAfter: '<p>ab<font style="color: rgb(255, 0, 0);">[]\u200B</font>cd</p>',
        });
    });
    it('should get ready to type with a different background color', async () => {
        await testEditor(BasicEditor, {
            contentBefore: '<p>ab[]cd</p>',
            stepFunction: setColor('rgb(255, 0, 0)', 'backgroundColor'),
            contentAfter: '<p>ab<font style="background-color: rgb(255, 0, 0);">[]\u200B</font>cd</p>',
        });
    });
    it('should apply a color on empty selection', async () => {
        await testEditor(BasicEditor, {
            contentBefore: '<p>[<br></p><p><br></p><p>]<br></p>',
            stepFunction: setColor('rgb(255, 0, 0)', 'color'),
            contentAfterEdit: '<p>[<font data-oe-zws-empty-inline="" style="color: rgb(255, 0, 0);">\u200B</font></p>' +
                              '<p><font data-oe-zws-empty-inline="" style="color: rgb(255, 0, 0);">\u200B</font></p>' +
                              '<p>]<font data-oe-zws-empty-inline="" style="color: rgb(255, 0, 0);">\u200B</font></p>',
            contentAfter: '<p>[</p><p></p><p>]</p>',
        });
    });
    it('should apply a background color on empty selection', async () => {
        await testEditor(BasicEditor, {
            contentBefore: '<p>[<br></p><p><br></p><p>]<br></p>',
            stepFunction: setColor('rgb(255, 0, 0)', 'backgroundColor'),
            contentAfterEdit: '<p>[<font data-oe-zws-empty-inline="" style="background-color: rgb(255, 0, 0);">\u200B</font></p>' +
                              '<p><font data-oe-zws-empty-inline="" style="background-color: rgb(255, 0, 0);">\u200B</font></p>' +
                              '<p>]<font data-oe-zws-empty-inline="" style="background-color: rgb(255, 0, 0);">\u200B</font></p>',
            contentAfter: '<p>[</p><p></p><p>]</p>',
        });
    });
    it('should not merge line on background color change', async () => {
        await testEditor(BasicEditor, {
            contentBefore: '<p><strong>[abcd</strong><br><strong>efghi]</strong></p>',
            stepFunction: setColor('rgb(255, 0, 0)', 'backgroundColor'),
            contentAfter: '<p><strong><font style="background-color: rgb(255, 0, 0);">[abcd</font></strong><br>' +
                          '<strong><font style="background-color: rgb(255, 0, 0);">efghi]</font></strong></p>',
        });
    });
    it('should not merge line on color change', async () => {
        await testEditor(BasicEditor, {
            contentBefore: '<p><strong>[abcd</strong><br><strong>efghi]</strong></p>',
            stepFunction: setColor('rgb(255, 0, 0)', 'color'),
            contentAfter: '<p><strong><font style="color: rgb(255, 0, 0);">[abcd</font></strong><br>' +
                          '<strong><font style="color: rgb(255, 0, 0);">efghi]</font></strong></p>',
        });
    });
    it('should not apply color on an uneditable element', async () => {
        await testEditor(BasicEditor, {
            contentBefore: '<p>[a</p><p contenteditable="false">b</p><p>c]</p>',
            stepFunction: setColor('rgb(255, 0, 0)', 'color'),
            contentAfter: unformat(`
                <p><font style="color: rgb(255, 0, 0);">[a</font></p>
                <p contenteditable="false">b</p>
                <p><font style="color: rgb(255, 0, 0);">c]</font></p>
            `),
        });
    });
    it('should not apply background color on an uneditable selected cell in a table', async () => {
        await testEditor(BasicEditor, {
            contentBefore: unformat(`
                <table><tbody>
                    <tr><td class="o_selected_td">[ab</td></tr>
                    <tr><td contenteditable="false" class="o_selected_td">cd</td></tr>
                    <tr><td class="o_selected_td">ef]</td></tr>
                </tbody></table>
            `),
            stepFunction: setColor('rgb(255, 0, 0)', 'backgroundColor'),
            contentAfter: unformat(`
                <table><tbody>
                    <tr><td style="background-color: rgb(255, 0, 0);">[]ab</td></tr>
                    <tr><td contenteditable="false">cd</td></tr>
                    <tr><td style="background-color: rgb(255, 0, 0);">ef</td></tr>
                </tbody></table>
            `),
        });
    });
    it('should remove font tag after removing font color', async () => {
        await testEditor(BasicEditor, {
            contentBefore: '<p><font style="color: rgb(255, 0, 0);">[abcabc]</font></p>',
            stepFunction: setColor('', 'color'),
            contentAfter: '<p>[abcabc]</p>',
        });
        await testEditor(BasicEditor, {
            contentBefore: '<p><font class="text-400">[abcabc]</font></p>',
            stepFunction: setColor('', 'color'),
            contentAfter: '<p>[abcabc]</p>',
        });
    });
    it('should remove font tag after removing background color applied as style', async () => {
        await testEditor(BasicEditor, {
            contentBefore: '<p><font style="background-color: rgb(255, 0, 0);">[abcabc]</font></p>',
            stepFunction: setColor('', 'backgroundColor'),
            contentAfter: '<p>[abcabc]</p>',
        });
        await testEditor(BasicEditor, {
            contentBefore: '<p><font class="bg-200">[abcabc]</font></p>',
            stepFunction: setColor('', 'backgroundColor'),
            contentAfter: '<p>[abcabc]</p>',
        });
    });
    it('should remove font tag if font-color and background-color both are removed one by one', async () => {
        await testEditor(BasicEditor, {
            contentBefore: '<p><font style="color: rgb(255, 0, 0);" class="bg-200">[abcabc]</font></p>',
            stepFunction: setColor('','backgroundColor') && setColor('','color'),
            contentAfter: '<p>[abcabc]</p>',
        });
        await testEditor(BasicEditor, {
            contentBefore: '<p><font style="background-color: rgb(255, 0, 0);" class="text-900">[abcabc]</font></p>',
            stepFunction: setColor('','color') && setColor('','backgroundColor'),
            contentAfter: '<p>[abcabc]</p>',
        });
    });
    it('should remove font tag after removing gradient color applied as style', async () => {
        await testEditor(BasicEditor, {
            contentBefore: '<p><font style="background-image: linear-gradient(135deg, rgb(214, 255, 127) 0%, rgb(0, 179, 204) 100%);">[abcabc]</font></p>',
            stepFunction: setColor('', 'backgroundColor'),
            contentAfter: '<p>[abcabc]</p>',
        });
        await testEditor(BasicEditor, {
            contentBefore: '<p><font class="text-gradient" style="background-image: linear-gradient(135deg, rgb(214, 255, 127) 0%, rgb(0, 179, 204) 100%);">[abcabc]</font></p>',
            stepFunction: setColor('', 'color'),
            contentAfter: '<p>[abcabc]</p>',
        });
    });
    it('Shall not apply font tag to t nodes (protects if else nodes separation)', async () => {
        await testEditor(BasicEditor, {
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
            stepFunction: setColor('red', 'backgroundColor'),
            contentAfter: unformat(`
                <p>
                    <t t-if="object.partner_id.parent_id">
                        <t t-out="object.partner_id.parent_id.name or ''" style="background-color: red;">
                            <font style="background-color: red;">[AzureInterior</font>
                        </t>
                    </t>
                    <t t-else="">
                        <t t-out="object.partner_id.name or ''" style="background-color: red;">
                            <font style="background-color: red;">BrandonFreeman]</font>
                        </t>
                    </t>
                </p>
            `),
        });
    });
    it("should apply text color whithout interrupting gradient background color on selected text", async () => {
        await testEditor(BasicEditor, {
            contentBefore: '<p><font style="background-image: linear-gradient(135deg, rgb(214, 255, 127) 0%, rgb(0, 179, 204) 100%);">ab[ca]bc</font></p>',
            stepFunction: setColor("rgb(255, 0, 0)", "color"),
            contentAfter: '<p><font style="background-image: linear-gradient(135deg, rgb(214, 255, 127) 0%, rgb(0, 179, 204) 100%);">ab<font style="color: rgb(255, 0, 0);">[ca]</font>bc</font></p>',
        });
    });
    it("should apply background color whithout interrupting gradient text color on selected text", async () => {
        await testEditor(BasicEditor, {
            contentBefore: '<p><font class="text-gradient" style="background-image: linear-gradient(135deg, rgb(214, 255, 127) 0%, rgb(0, 179, 204) 100%);">ab[ca]bc</font></p>',
            stepFunction: setColor("rgb(255, 0, 0)", "backgroundColor"),
            contentAfter: '<p><font class="text-gradient" style="background-image: linear-gradient(135deg, rgb(214, 255, 127) 0%, rgb(0, 179, 204) 100%);">ab<font style="background-color: rgb(255, 0, 0);">[ca]</font>bc</font></p>',
        });
    });
    it("should apply background color whithout interrupting gradient background color on selected text", async () => {
        await testEditor(BasicEditor, {
            contentBefore: '<p><font style="background-image: linear-gradient(135deg, rgb(214, 255, 127) 0%, rgb(0, 179, 204) 100%);">ab[ca]bc</font></p>',
            stepFunction: setColor("rgb(255, 0, 0)", "backgroundColor"),
            contentAfter: '<p><font style="background-image: linear-gradient(135deg, rgb(214, 255, 127) 0%, rgb(0, 179, 204) 100%);">ab<font style="background-color: rgb(255, 0, 0);">[ca]</font>bc</font></p>',
        });
    });
    it("should apply text color whithout interrupting gradient text color on selected text", async () => {
        await testEditor(BasicEditor, {
            contentBefore: '<p><font class="text-gradient" style="background-image: linear-gradient(135deg, rgb(214, 255, 127) 0%, rgb(0, 179, 204) 100%);">ab[ca]bc</font></p>',
            stepFunction: setColor("rgb(255, 0, 0)", "color"),
            contentAfter:  '<p><font class="text-gradient" style="background-image: linear-gradient(135deg, rgb(214, 255, 127) 0%, rgb(0, 179, 204) 100%);">ab<font style="-webkit-text-fill-color: rgb(255, 0, 0); color: rgb(255, 0, 0);">[ca]</font>bc</font></p>',
        });
    });
    it("should break gradient color on selected text", async () => {
        await testEditor(BasicEditor, {
            contentBefore: '<p><font class="text-gradient" style="background-image: linear-gradient(135deg, rgb(214, 255, 127) 0%, rgb(0, 179, 204) 100%);">ab[ca]bc</font></p>',
            stepFunction: setColor("linear-gradient(135deg, rgb(255, 174, 127) 0%, rgb(109, 204, 0) 100%)", "backgroundColor"),
            contentAfter:  '<p><font class="text-gradient" style="background-image: linear-gradient(135deg, rgb(214, 255, 127) 0%, rgb(0, 179, 204) 100%);">ab</font>' +
                            '<font style="background-image: linear-gradient(135deg, rgb(255, 174, 127) 0%, rgb(109, 204, 0) 100%);">[ca]</font>' +
                            '<font class="text-gradient" style="background-image: linear-gradient(135deg, rgb(214, 255, 127) 0%, rgb(0, 179, 204) 100%);">bc</font></p>',
        });
    });
    it("should update the gradient color and remove the nested background color to make the gradient visible", async () => {
        await testEditor(BasicEditor, {
            contentBefore: '<p><font style="background-image: linear-gradient(135deg, rgb(214, 255, 127) 0%, rgb(0, 179, 204) 100%);"><font style="background-color: rgb(255, 0, 0);">[abc]</font></font></p>',
            stepFunction: setColor("linear-gradient(135deg, rgb(255, 174, 127) 0%, rgb(109, 204, 0) 100%)", "backgroundColor"),
            contentAfter:  '<p><font style="background-image: linear-gradient(135deg, rgb(255, 174, 127) 0%, rgb(109, 204, 0) 100%);">[abc]</font></p>',
        });
    });
    it("should update the gradient text color and remove the nested text color to make the gradient visible", async () => {
        await testEditor(BasicEditor, {
            contentBefore: '<p><font class="text-gradient" style="background-image: linear-gradient(135deg, rgb(214, 255, 127) 0%, rgb(0, 179, 204) 100%);"><font style="-webkit-text-fill-color: rgb(255, 0, 0); color: rgb(255, 0, 0);">[abc]</font></font></p>',
            stepFunction: setColor("linear-gradient(135deg, rgb(255, 174, 127) 0%, rgb(109, 204, 0) 100%)", "color"),
            contentAfter:  '<p><font class="text-gradient" style="background-image: linear-gradient(135deg, rgb(255, 174, 127) 0%, rgb(109, 204, 0) 100%);">[abc]</font></p>',
        });
    });
    it("should apply gradient color when a when background color is applied on span", async () => {
        await testEditor(BasicEditor, {
            contentBefore: '<p><span style="background-color: rgb(255, 0, 0)">ab[ca]bc</span></p>',
            stepFunction: setColor("linear-gradient(135deg, rgb(255, 174, 127) 0%, rgb(109, 204, 0) 100%)", "color"),
            contentAfter: '<p><span style="background-color: rgb(255, 0, 0)">ab<font class="text-gradient" style="background-image: linear-gradient(135deg, rgb(255, 174, 127) 0%, rgb(109, 204, 0) 100%);">[ca]</font>bc</span></p>',
        });
    });
    it("should apply a gradient color to a slice of text in a span", async () => {
        await testEditor(BasicEditor, {
            contentBefore: '<p><span class="a">ab[ca]bc</span></p>',
            stepFunction: setColor("linear-gradient(135deg, rgb(255, 174, 127) 0%, rgb(109, 204, 0) 100%)", "color"),
            contentAfter: '<p><span class="a">ab<font class="text-gradient" style="background-image: linear-gradient(135deg, rgb(255, 174, 127) 0%, rgb(109, 204, 0) 100%);">[ca]</font>bc</span></p>',
        });
    });
    it("should applied background color to slice of text in a span without interrupting gradient background color", async () => {
        await testEditor(BasicEditor, {
            contentBefore: '<p><font style="background-image: linear-gradient(135deg, rgb(214, 255, 127) 0%, rgb(0, 179, 204) 100%);"><span class="a">ab[ca]bc</span><font></p>',
            stepFunction: setColor("rgb(255, 0, 0)", "backgroundColor"),
            contentAfter: '<p><font style="background-image: linear-gradient(135deg, rgb(214, 255, 127) 0%, rgb(0, 179, 204) 100%);"><span class="a">ab<font style="background-color: rgb(255, 0, 0);">[ca]</font>bc</span></font></p>',
        });
    });
    it("should break a gradient and apply gradient background color to a slice of text within a span", async () => {
        await testEditor(BasicEditor, {
            contentBefore: '<p><font style="background-image: linear-gradient(135deg, rgb(214, 255, 127) 0%, rgb(0, 179, 204) 100%);"><span class="a">ab<font style="background-color: rgb(255, 0, 0);">[ca]</font>bc</span></font></p>',
            stepFunction: setColor("linear-gradient(135deg, rgb(255, 174, 127) 0%, rgb(109, 204, 0) 100%)", "color"),
            contentAfter: '<p><font style="background-image: linear-gradient(135deg, rgb(214, 255, 127) 0%, rgb(0, 179, 204) 100%);"><span class="a">ab</span></font>' +
                        '<font style="background-image: linear-gradient(135deg, rgb(255, 174, 127) 0%, rgb(109, 204, 0) 100%);" class="text-gradient"><span class="a"><font style="background-color: rgb(255, 0, 0);">[ca]</font></span></font>' +
                        '<font style="background-image: linear-gradient(135deg, rgb(214, 255, 127) 0%, rgb(0, 179, 204) 100%);"><span class="a">bc</span></font></p>',
        });
    });
    it("should apply gradient color on selected text", async () => {
        await testEditor(BasicEditor, {
            contentBefore: '<div style="background-image:none"><p>[ab<strong>cd</strong>ef]</p></div>',
            stepFunction: setColor("linear-gradient(135deg, rgb(255, 174, 127) 0%, rgb(109, 204, 0) 100%)", "backgroundColor"),
            contentAfter: '<div style="background-image:none"><p><font style="background-image: linear-gradient(135deg, rgb(255, 174, 127) 0%, rgb(109, 204, 0) 100%);">[ab<strong>cd</strong>ef]</font></p></div>'
        });
    });
    it("should apply gradient text color on selected text", async () => {
        await testEditor(BasicEditor, {
            contentBefore: '<div style="background-image:none"><p>[ab<strong>cd</strong>ef]</p></div>',
            stepFunction: setColor("linear-gradient(135deg, rgb(255, 174, 127) 0%, rgb(109, 204, 0) 100%)", "color"),
            contentAfter: '<div style="background-image:none"><p><font class="text-gradient" style="background-image: linear-gradient(135deg, rgb(255, 174, 127) 0%, rgb(109, 204, 0) 100%);">[ab<strong>cd</strong>ef]</font></p></div>'
        });
    });
});
describe('rgbToHex', () => {
    it('should convert an rgb color to hexadecimal', async () => {
        window.chai.expect(rgbToHex('rgb(0, 0, 255)')).to.be.equal('#0000ff');
        window.chai.expect(rgbToHex('rgb(0,0,255)')).to.be.equal('#0000ff');
    });
    it('should convert an rgba color to hexadecimal (background is hexadecimal)', async () => {
        const parent = document.createElement('div');
        const node = document.createElement('div');
        parent.style.backgroundColor = '#ff0000'; // red, should be irrelevant
        node.style.backgroundColor = '#0000ff'; // blue
        parent.append(node);
        document.body.append(parent);
        // white with 50% opacity over blue = light blue
        window.chai.expect(rgbToHex('rgba(255, 255, 255, 0.5)', node)).to.be.equal('#7f7fff');
        parent.remove();
    });
    it('should convert an rgba color to hexadecimal (background is color name)', async () => {
        const parent = document.createElement('div');
        const node = document.createElement('div');
        parent.style.backgroundColor = '#ff0000'; // red, should be irrelevant
        node.style.backgroundColor = 'blue'; // blue
        parent.append(node);
        document.body.append(parent);
        // white with 50% opacity over blue = light blue
        window.chai.expect(rgbToHex('rgba(255, 255, 255, 0.5)', node)).to.be.equal('#7f7fff');
        parent.remove();
    });
    it('should convert an rgba color to hexadecimal (background is rgb)', async () => {
        const parent = document.createElement('div');
        const node = document.createElement('div');
        parent.style.backgroundColor = '#ff0000'; // red, should be irrelevant
        node.style.backgroundColor = 'rgb(0, 0, 255)'; // blue
        parent.append(node);
        document.body.append(parent);
        // white with 50% opacity over blue = light blue
        window.chai.expect(rgbToHex('rgba(255, 255, 255, 0.5)', node)).to.be.equal('#7f7fff');
        parent.remove();
    });
    it('should convert an rgba color to hexadecimal (background is rgba)', async () => {
        const parent = document.createElement('div');
        const node = document.createElement('div');
        parent.style.backgroundColor = 'rgb(255, 0, 0)'; // red
        node.style.backgroundColor = 'rgba(0, 0, 255, 0.5)'; // blue
        parent.append(node);
        document.body.append(parent);
        // white with 50% opacity over blue with 50% opacity over red = light purple
        window.chai.expect(rgbToHex('rgba(255, 255, 255, 0.5)', node)).to.be.equal('#bf7fbf');
        parent.remove();
    });
});
