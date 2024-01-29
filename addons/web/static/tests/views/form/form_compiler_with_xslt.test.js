/** @odoo-module **/

import { ViewCompilerWithXSLT } from "@web/views/view_compiler_with_xslt";
import { expect, test } from "@odoo/hoot";
import { FormCompiler } from "@web/views/form/form_compiler";

const parser = new DOMParser();
function compileTemplate(arch, params) {
    const xml = parser.parseFromString(arch, "text/xml");
    const newCompiler = new ViewCompilerWithXSLT({ form: xml.documentElement });
    const oldCompiler = new FormCompiler({ form: xml.documentElement });
    return {
        withXSLT: newCompiler.compile("form", params).outerHTML,
        withoutXSLT: oldCompiler.compile("form", params).outerHTML,
    };
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

test("properly compile simple div", async () => {
    const arch = /*xml*/ `<form><div>lol</div></form>`;
    const expected = /*xml*/ `<t><div class="o_form_renderer o_form_nosheet" t-att-class="__comp__.props.class" t-attf-class="{{__comp__.props.record.isInEdition ? 'o_form_editable' : 'o_form_readonly'}} d-block {{ __comp__.props.record.dirty ? 'o_form_dirty' : !__comp__.props.record.isNew ? 'o_form_saved' : '' }}" t-ref="compiled_view_root"><div>lol</div></div></t>`;
    expect(compileTemplate(arch).withXSLT).toBe(expected);
});

test("properly compile simple sheet", async () => {
    const arch = /*xml*/ `<form><sheet/></form>`;
    const expected = /*xml*/ `<t><div class="o_form_renderer" t-att-class="__comp__.props.class" t-attf-class="{{__comp__.props.record.isInEdition ? 'o_form_editable' : 'o_form_readonly'}} d-flex {{ __comp__.uiService.size &lt; 6 ? 'flex-column' : 'flex-nowrap h-100' }} {{ __comp__.props.record.dirty ? 'o_form_dirty' : !__comp__.props.record.isNew ? 'o_form_saved' : '' }}" t-ref="compiled_view_root"><sheet/></div></t>`;
    expect(compileTemplate(arch).withXSLT).toBe(expected);
});

test("copy form attributes", async () => {
    const arch = /*xml*/ `<form class="a" attr="x" id="2"/>`;
    const expected = /*xml*/ `<t><div class="o_form_renderer" t-att-class="__comp__.props.class" t-attf-class="{{__comp__.props.record.isInEdition ? 'o_form_editable' : 'o_form_readonly'}} d-flex {{ __comp__.uiService.size &lt; 6 ? 'flex-column' : 'flex-nowrap h-100' }} {{ __comp__.props.record.dirty ? 'o_form_dirty' : !__comp__.props.record.isNew ? 'o_form_saved' : '' }}" t-ref="compiled_view_root" /></t>`;
    expect(compileTemplate(arch).withXSLT).toBe(expected);
});

test("pass param", async () => {
    const arch = /*xml*/ `<span/>`;
    const expected = /*xml*/ `<t><span>1</span></t>`;
    expect(compileTemplate(arch, { a: 1 }).withXSLT).toBe(expected);
});

test("comment are not kept", async () => {
    const arch = /*xml*/ `<span><!-- comment --></span>`;
    const expected = /*xml*/ `<t><span/></t>`;
    expect(compileTemplate(arch).withXSLT).toBe(expected);
});

test("text are not kept", async () => {
    const arch = /*xml*/ `<span>text</span>`;
    const expected = /*xml*/ `<t><span>text</span></t>`;
    expect(compileTemplate(arch).withXSLT).toBe(expected);
});

test("deep hierarchy", async () => {
    const arch = /*xml*/ `
        <div>
            <div id="1">
                <div/>
                <div/>
            </div>
        </div>
    `;
    const expected = /*xml*/ `<t><div>
            <div id="1">
                <div/>
                <div/>
            </div>
        </div></t>`;
    expect(compileTemplate(arch).withXSLT).toBe(expected);
});

test("tag field", async () => {
    const arch = /*xml*/ `<field field_id="display_name" name="display_name"/>`;
    const expected = /*xml*/ `<t><Field id="'display_name'" name="'display_name'" record="__comp__.props.record" fieldInfo="__comp__.props.archInfo.fieldNodes['display_name']" readonly="__comp__.props.archInfo.activeActions?.edit === false and !__comp__.props.record.isNew"/></t>`;
    expect(compileTemplate(arch).withXSLT).toBe(expected);
});

test("tag field 2", async () => {
    const arch = /*xml*/ `<form><field name="display_name" widget="widget_name"/></form>`;
    expect(compileTemplate(arch).withXSLT).toBe(compileTemplate(arch).withoutXSLT);
});

test("tag field 3", async () => {
    const arch = /*xml*/ `<form><field name="display_name" widget="widget_name"/></form>`;
    expect(compileTemplate(arch).withXSLT).toBe(compileTemplate(arch).withoutXSLT);
});
