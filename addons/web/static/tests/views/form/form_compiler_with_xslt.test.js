/** @odoo-module **/

import { ViewCompilerWithXSLT } from "@web/views/view_compiler_with_xslt";
import { expect, test } from "@odoo/hoot";

const parser = new DOMParser();
function compileTemplate(arch) {
    const xml = parser.parseFromString(arch, "text/xml");
    const compiler = new ViewCompilerWithXSLT({ form: xml.documentElement });
    return compiler.compile("form").outerHTML;
}

// QUnit.assert.areEquivalent = function (template1, template2) {
//     if (template1.replace(/\s/g, "") === template2.replace(/\s/g, "")) {
//         QUnit.assert.ok(true);
//     } else {
//         QUnit.assert.strictEqual(template1, template2);
//     }
// };

// QUnit.assert.areContentEquivalent = function (template, content) {
//     const doc = parser.parseFromString(template, "text/xml");
//     const templateContent = doc.documentElement.firstChild.innerHTML;
//     QUnit.assert.areEquivalent(templateContent, content);
// };

test("properly compile simple div", async (assert) => {
    const arch = /*xml*/ `<form><div>lol</div></form>`;
    const expected = /*xml*/ `<t><div class="o_form_renderer o_form_nosheet" t-att-class="__comp__.props.class" t-attf-class="{{__comp__.props.record.isInEdition ? 'o_form_editable' : 'o_form_readonly'}} d-block {{ __comp__.props.record.dirty ? 'o_form_dirty' : !__comp__.props.record.isNew ? 'o_form_saved' : '' }}" t-ref="compiled_view_root"><div>lol</div></div></t>`;
    expect(compileTemplate(arch)).toBe(expected);
});

test("properly compile simple sheet", async (assert) => {
    const arch = /*xml*/ `<form><sheet/></form>`;
    const expected = /*xml*/ `<t><div class="o_form_renderer" t-att-class="__comp__.props.class" t-attf-class="{{__comp__.props.record.isInEdition ? 'o_form_editable' : 'o_form_readonly'}} d-flex {{ __comp__.uiService.size &lt; 6 ? 'flex-column' : 'flex-nowrap h-100' }} {{ __comp__.props.record.dirty ? 'o_form_dirty' : !__comp__.props.record.isNew ? 'o_form_saved' : '' }}" t-ref="compiled_view_root"><sheet/></div></t>`;
    expect(compileTemplate(arch)).toBe(expected);
});
