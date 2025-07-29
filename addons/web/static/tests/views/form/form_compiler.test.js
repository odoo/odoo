import { describe, expect, test } from "@odoo/hoot";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";

import { createElement } from "@web/core/utils/xml";
import { FormCompiler } from "@web/views/form/form_compiler";

describe.current.tags("headless");

function compileTemplate(arch) {
    const parser = new DOMParser();
    const xml = parser.parseFromString(arch, "text/xml");
    const compiler = new FormCompiler({ form: xml.documentElement });
    return compiler.compile("form");
}

test("properly compile simple div", () => {
    const arch = /*xml*/ `<form><div>lol</div></form>`;
    const expected = /*xml*/ `
        <t t-translation="off">
            <div class="o_form_renderer o_form_nosheet" t-att-class="__comp__.props.class" t-attf-class="{{__comp__.props.record.isInEdition ? 'o_form_editable' : 'o_form_readonly'}} d-block {{ __comp__.props.record.dirty ? 'o_form_dirty' : !__comp__.props.record.isNew ? 'o_form_saved' : '' }}" t-ref="compiled_view_root">
                <div>lol</div>
            </div>
        </t>
    `;
    expect(compileTemplate(arch)).toHaveOuterHTML(expected);
});

test("label with empty string compiles to FormLabel with empty string", () => {
    const arch = /*xml*/ `<form><field field_id="test" name="test"/><label for="test" string=""/></form>`;
    const expected = /*xml*/ `
        <t t-translation="off">
            <div class="o_form_renderer o_form_nosheet" t-att-class="__comp__.props.class" t-attf-class="{{__comp__.props.record.isInEdition ? 'o_form_editable' : 'o_form_readonly'}} d-block {{ __comp__.props.record.dirty ? 'o_form_dirty' : !__comp__.props.record.isNew ? 'o_form_saved' : '' }}" t-ref="compiled_view_root">
                <Field id="'test'" name="'test'" record="__comp__.props.record" fieldInfo="__comp__.props.archInfo.fieldNodes['test']" readonly="__comp__.props.readonly"/>
                <FormLabel id="'test'" fieldName="'test'" record="__comp__.props.record" fieldInfo="__comp__.props.archInfo.fieldNodes['test']" className="&quot;&quot;" string="\`\`" />
            </div>
        </t>
    `;
    expect(compileTemplate(arch)).toHaveOuterHTML(expected);
});

test("properly compile simple div with field", () => {
    const arch = /*xml*/ `<form><div class="someClass">lol<field field_id="display_name" name="display_name"/></div></form>`;
    const expected = /*xml*/ `
        <t t-translation="off">
            <div class="o_form_renderer o_form_nosheet" t-att-class="__comp__.props.class" t-attf-class="{{__comp__.props.record.isInEdition ? 'o_form_editable' : 'o_form_readonly'}} d-block {{ __comp__.props.record.dirty ? 'o_form_dirty' : !__comp__.props.record.isNew ? 'o_form_saved' : '' }}" t-ref="compiled_view_root">
                <div class="someClass">
                    lol
                    <Field id="'display_name'" name="'display_name'" record="__comp__.props.record" fieldInfo="__comp__.props.archInfo.fieldNodes['display_name']" readonly="__comp__.props.readonly"/>
                </div>
            </div>
        </t>
    `;
    expect(compileTemplate(arch)).toHaveOuterHTML(expected);
});

test("properly compile inner groups", () => {
    const arch = /*xml*/ `
        <form>
            <group>
                <group><field field_id="display_name" name="display_name"/></group>
                <group><field field_id="charfield" name="charfield"/></group>
            </group>
        </form>
    `;
    const expected = /*xml*/ `
        <t t-translation="off">
            <div class="o_form_renderer o_form_nosheet" t-att-class="__comp__.props.class" t-attf-class="{{__comp__.props.record.isInEdition ? 'o_form_editable' : 'o_form_readonly'}} d-block {{ __comp__.props.record.dirty ? 'o_form_dirty' : !__comp__.props.record.isNew ? 'o_form_saved' : '' }}" t-ref="compiled_view_root">
                <OuterGroup>
                    <t t-set-slot="item_0" type="'item'" sequence="0" t-slot-scope="scope" isVisible="true" itemSpan="1">
                        <InnerGroup class="scope &amp;&amp; scope.className">
                            <t t-set-slot="item_0" type="'item'" sequence="0" t-slot-scope="scope" props="{id:'display_name',fieldName:'display_name',record:__comp__.props.record,string:__comp__.props.record.fields.display_name.string,fieldInfo:__comp__.props.archInfo.fieldNodes['display_name']}" Component="__comp__.constructor.components.FormLabel" subType="'item_component'" isVisible="true" itemSpan="2">
                                <Field id="'display_name'" name="'display_name'" record="__comp__.props.record" fieldInfo="__comp__.props.archInfo.fieldNodes['display_name']" readonly="__comp__.props.readonly" class="scope &amp;&amp; scope.className"/>
                            </t>
                        </InnerGroup>
                    </t>
                    <t t-set-slot="item_1" type="'item'" sequence="1" t-slot-scope="scope" isVisible="true" itemSpan="1">
                        <InnerGroup class="scope &amp;&amp; scope.className">
                            <t t-set-slot="item_0" type="'item'" sequence="0" t-slot-scope="scope" props="{id:'charfield',fieldName:'charfield',record:__comp__.props.record,string:__comp__.props.record.fields.charfield.string,fieldInfo:__comp__.props.archInfo.fieldNodes['charfield']}" Component="__comp__.constructor.components.FormLabel" subType="'item_component'" isVisible="true" itemSpan="2">
                                <Field id="'charfield'" name="'charfield'" record="__comp__.props.record" fieldInfo="__comp__.props.archInfo.fieldNodes['charfield']" readonly="__comp__.props.readonly" class="scope &amp;&amp; scope.className"/>
                            </t>
                        </InnerGroup>
                    </t>
                </OuterGroup>
            </div>
        </t>
    `;
    expect(compileTemplate(arch)).toHaveOuterHTML(expected);
});

test("properly compile attributes with nested forms", () => {
    const arch = /*xml*/ `
        <form>
            <group>
                <group>
                    <form>
                        <div>
                            <field field_id="test" name="test"/>
                        </div>
                    </form>
                </group>
            </group>
        </form>
    `;
    const expected = /*xml*/ `
        <t t-translation="off">
            <div class="o_form_renderer o_form_nosheet" t-att-class="__comp__.props.class" t-attf-class="{{__comp__.props.record.isInEdition ? 'o_form_editable' : 'o_form_readonly'}} d-block {{ __comp__.props.record.dirty ? 'o_form_dirty' : !__comp__.props.record.isNew ? 'o_form_saved' : '' }}" t-ref="compiled_view_root">
                <OuterGroup>
                    <t t-set-slot="item_0" type="'item'" sequence="0" t-slot-scope="scope" isVisible="true" itemSpan="1">
                        <InnerGroup class="scope &amp;&amp; scope.className">
                            <t t-set-slot="item_0" type="'item'" sequence="0" t-slot-scope="scope" isVisible="true" itemSpan="1">
                                <div class="o_form_renderer o_form_nosheet" t-att-class="__comp__.props.class" t-attf-class="{{__comp__.props.record.isInEdition ? 'o_form_editable' : 'o_form_readonly'}} d-block {{ __comp__.props.record.dirty ? 'o_form_dirty' : !__comp__.props.record.isNew ? 'o_form_saved' : '' }} {{scope &amp;&amp; scope.className || &quot;&quot; }}">
                                    <div><Field id="'test'" name="'test'" record="__comp__.props.record" fieldInfo="__comp__.props.archInfo.fieldNodes['test']" readonly="__comp__.props.readonly"/></div>
                                </div>
                            </t>
                        </InnerGroup>
                    </t>
                </OuterGroup>
            </div>
        </t>
    `;
    expect(compileTemplate(arch)).toHaveOuterHTML(expected);
});

test("properly compile notebook", () => {
    const arch = /*xml*/ `
        <form>
            <notebook>
                <page name="p1" string="Page1"><field field_id="charfield" name="charfield"/></page>
                <page name="p2" string="Page2"><field field_id="display_name" name="display_name"/></page>
            </notebook>
        </form>
    `;
    const expected = /*xml*/ `
        <t t-translation="off">
            <div class="o_form_renderer o_form_nosheet" t-att-class="__comp__.props.class" t-attf-class="{{__comp__.props.record.isInEdition ? 'o_form_editable' : 'o_form_readonly'}} d-block {{ __comp__.props.record.dirty ? 'o_form_dirty' : !__comp__.props.record.isNew ? 'o_form_saved' : '' }}" t-ref="compiled_view_root">
                <Notebook defaultPage="__comp__.props.record.isNew ? undefined : __comp__.props.activeNotebookPages[0]" onPageUpdate="(page) =&gt; __comp__.props.onNotebookPageChange(0, page)">
                    <t t-set-slot="page_1" title="\`Page1\`" name="\`p1\`" isVisible="true">
                        <Field id="'charfield'" name="'charfield'" record="__comp__.props.record" fieldInfo="__comp__.props.archInfo.fieldNodes['charfield']" readonly="__comp__.props.readonly"/>
                    </t>
                    <t t-set-slot="page_2" title="\`Page2\`" name="\`p2\`" isVisible="true">
                        <Field id="'display_name'" name="'display_name'" record="__comp__.props.record" fieldInfo="__comp__.props.archInfo.fieldNodes['display_name']" readonly="__comp__.props.readonly"/>
                    </t>
                </Notebook>
            </div>
        </t>
    `;
    expect(compileTemplate(arch)).toHaveOuterHTML(expected);
});

test("properly compile field without placeholder", () => {
    const arch = /*xml*/ `
        <form>
            <field field_id="display_name" name="display_name" placeholder="e.g. Contact's Name or //someinfo..."/>
        </form>
    `;
    const expected = /*xml*/ `
        <t t-translation="off">
            <div class="o_form_renderer o_form_nosheet" t-att-class="__comp__.props.class" t-attf-class="{{__comp__.props.record.isInEdition ? 'o_form_editable' : 'o_form_readonly'}} d-block {{ __comp__.props.record.dirty ? 'o_form_dirty' : !__comp__.props.record.isNew ? 'o_form_saved' : '' }}" t-ref="compiled_view_root">
                <Field id="'display_name'" name="'display_name'" record="__comp__.props.record" fieldInfo="__comp__.props.archInfo.fieldNodes['display_name']" readonly="__comp__.props.readonly"/>
            </div>
        </t>
    `;
    expect(compileTemplate(arch)).toHaveOuterHTML(expected);
});

test("properly compile no sheet", () => {
    const arch = /*xml*/ `
        <form>
            <header>someHeader</header>
            <div>someDiv</div>
        </form>
    `;
    const expected = /*xml*/ `
        <t t-translation="off">
            <div class="o_form_renderer o_form_nosheet" t-att-class="__comp__.props.class" t-attf-class="{{__comp__.props.record.isInEdition ? 'o_form_editable' : 'o_form_readonly'}} d-block {{ __comp__.props.record.dirty ? 'o_form_dirty' : !__comp__.props.record.isNew ? 'o_form_saved' : '' }}" t-ref="compiled_view_root">
                <div t-att-class="{ 'shadow-sm': __comp__.state.isStatusbarStickyPinned }" class="o_form_statusbar d-flex justify-content-between py-2">
                    <StatusBarButtons/>
                </div>
                <div>someDiv</div>
            </div>
        </t>
    `;
    expect(compileTemplate(arch)).toHaveOuterHTML(expected);
});

test("properly compile sheet", () => {
    const arch = /*xml*/ `
        <form>
            <header>someHeader</header>
            <div>someDiv</div>
            <sheet>
                <div>inside sheet</div>
            </sheet>
            <div>after sheet</div>
        </form>
    `;
    const expected = /*xml*/ `
        <t t-translation="off">
            <div class="o_form_renderer" t-att-class="__comp__.props.class" t-attf-class="{{__comp__.props.record.isInEdition ? 'o_form_editable' : 'o_form_readonly'}} d-flex d-print-block {{ __comp__.uiService.size &lt; 5 ? &quot;flex-column&quot; : &quot;flex-nowrap h-100&quot; }} {{ __comp__.props.record.dirty ? 'o_form_dirty' : !__comp__.props.record.isNew ? 'o_form_saved' : '' }}" t-ref="compiled_view_root">
                <div t-on-scroll="__comp__.onScrollThrottled" class="o_form_sheet_bg">
                    <div t-att-class="{ 'shadow-sm': __comp__.state.isStatusbarStickyPinned }" class="o_form_statusbar d-flex justify-content-between py-2"><StatusBarButtons/></div>
                    <div>someDiv</div>
                    <div class="o_form_sheet position-relative">
                        <div>inside sheet</div>
                    </div>
                </div>
                <div>after sheet</div>
            </div>
        </t>
    `;
    expect(compileTemplate(arch)).toHaveOuterHTML(expected);
});

test("properly compile buttonBox invisible in sheet", () => {
    const arch = /*xml*/ `
        <form>
            <sheet>
                <div class="oe_button_box" name="button_box" invisible="'display_name' == 'plop'">
                    <div>Hello</div>
                </div>
            </sheet>
        </form>
    `;
    const expected = /*xml*/ `
        <t t-translation="off">
            <div class="o_form_renderer"
                 t-att-class="__comp__.props.class"
                 t-attf-class="{{__comp__.props.record.isInEdition ? 'o_form_editable' : 'o_form_readonly'}} d-flex d-print-block {{ __comp__.uiService.size &lt; 5 ? &quot;flex-column&quot; : &quot;flex-nowrap h-100&quot; }} {{ __comp__.props.record.dirty ? 'o_form_dirty' : !__comp__.props.record.isNew ? 'o_form_saved' : '' }}"
                 t-ref="compiled_view_root">
                <div t-on-scroll="__comp__.onScrollThrottled" class="o_form_sheet_bg">
                    <div class="o_form_sheet position-relative">
                    </div>
                </div>
            </div>
        </t>
    `;
    expect(compileTemplate(arch)).toHaveOuterHTML(expected);
});

test("properly compile invisible", () => {
    // cf python side: def transfer_node_to_modifiers
    // modifiers' string are evaluated to their boolean or array form
    // So the following arch may actually be written as:
    // ```<form>
    //      <field name="display_name" invisible="1" />
    //      <div class="visible3" invisible="0"/>
    //      <div invisible="display_name == 'take'"/>
    //    </form>````
    const arch = /*xml*/ `
        <form>
            <field field_id="display_name" name="display_name" invisible="True" />
            <div class="visible3" invisible="False"/>
            <div invisible="display_name == &quot;take&quot;"/>
        </form>
    `;
    const expected = /*xml*/ `
        <t t-translation="off">
            <div class="o_form_renderer o_form_nosheet" t-att-class="__comp__.props.class" t-attf-class="{{__comp__.props.record.isInEdition ? 'o_form_editable' : 'o_form_readonly'}} d-block {{ __comp__.props.record.dirty ? 'o_form_dirty' : !__comp__.props.record.isNew ? 'o_form_saved' : '' }}" t-ref="compiled_view_root">
                <div class="visible3"/>
                <div t-if="!__comp__.evaluateBooleanExpr(&quot;display_name == \\&quot;take\\&quot;&quot;,__comp__.props.record.evalContextWithVirtualIds)"/>
            </div>
        </t>
    `;
    expect(compileTemplate(arch)).toHaveOuterHTML(expected);
});

test("compile invisible containing string as domain", () => {
    const arch = /*xml*/ `
        <form>
            <field name="display_name" invisible="True"/>
            <div class="visible3" invisible="False"/>
            <div invisible="display_name == 'take'"/>
        </form>
    `;
    const expected = /*xml*/ `
        <t t-translation="off">
            <div class="o_form_renderer o_form_nosheet" t-att-class="__comp__.props.class" t-attf-class="{{__comp__.props.record.isInEdition ? 'o_form_editable' : 'o_form_readonly'}} d-block {{ __comp__.props.record.dirty ? 'o_form_dirty' : !__comp__.props.record.isNew ? 'o_form_saved' : '' }}" t-ref="compiled_view_root">
                <div class="visible3" />
                <div t-if="!__comp__.evaluateBooleanExpr(&quot;display_name == 'take'&quot;,__comp__.props.record.evalContextWithVirtualIds)"/>
            </div>
        </t>
    `;
    expect(compileTemplate(arch)).toHaveOuterHTML(expected);
});

test("properly compile status bar with content", () => {
    const arch = /*xml*/ `
        <form>
            <header><div>someDiv</div></header>
        </form>
    `;
    const expected = /*xml*/ `
        <t t-translation="off">
            <div class="o_form_renderer o_form_nosheet" t-att-class="__comp__.props.class" t-attf-class="{{__comp__.props.record.isInEdition ? 'o_form_editable' : 'o_form_readonly'}} d-block {{ __comp__.props.record.dirty ? 'o_form_dirty' : !__comp__.props.record.isNew ? 'o_form_saved' : '' }}" t-ref="compiled_view_root">
                <div t-att-class="{ 'shadow-sm': __comp__.state.isStatusbarStickyPinned }" class="o_form_statusbar d-flex justify-content-between py-2">
                    <StatusBarButtons>
                        <t t-set-slot="button_0" isVisible="true">
                            <div>someDiv</div>
                        </t>
                    </StatusBarButtons>
                </div>
            </div>
        </t>
    `;
    expect(compileTemplate(arch)).toHaveOuterHTML(expected);
});

test("properly compile status bar without content", () => {
    const arch = /*xml*/ `
        <form>
            <header></header>
        </form>
    `;
    const expected = /*xml*/ `
        <t t-translation="off">
            <div class="o_form_renderer o_form_nosheet" t-att-class="__comp__.props.class" t-attf-class="{{__comp__.props.record.isInEdition ? 'o_form_editable' : 'o_form_readonly'}} d-block {{ __comp__.props.record.dirty ? 'o_form_dirty' : !__comp__.props.record.isNew ? 'o_form_saved' : '' }}" t-ref="compiled_view_root">
                <div t-att-class="{ 'shadow-sm': __comp__.state.isStatusbarStickyPinned }" class="o_form_statusbar d-flex justify-content-between py-2">
                    <StatusBarButtons/>
                </div>
            </div>
        </t>
    `;
    expect(compileTemplate(arch)).toHaveOuterHTML(expected);
});

test("properly compile settings", () => {
    const arch = /*xml*/ `
        <form>
            <setting help="this is bar"
                     documentation="/applications/technical/web/settings/this_is_a_test.html"
                     company_dependent="1">
                <field field_id="bar" name="bar"/>
                <label>label with content</label>
            </setting>
        </form>
    `;
    const expected = /*xml*/ `
        <t t-translation="off">
            <div class="o_form_renderer o_form_nosheet" t-att-class="__comp__.props.class" t-attf-class="{{__comp__.props.record.isInEdition ? 'o_form_editable' : 'o_form_readonly'}} d-block {{ __comp__.props.record.dirty ? 'o_form_dirty' : !__comp__.props.record.isNew ? 'o_form_saved' : '' }}" t-ref="compiled_view_root">
                <Setting title="\`\`"
                        help="\`this is bar\`"
                        companyDependent="true"
                        documentation="\`/applications/technical/web/settings/this_is_a_test.html\`"
                        record="__comp__.props.record"
                        fieldInfo="__comp__.props.archInfo.fieldNodes['bar']"
                        fieldName="\`bar\`"
                        fieldId="\`bar\`"
                        string="\`\`"
                        addLabel="true">
                    <t t-set-slot="fieldSlot">
                        <Field id="'bar'"
                            name="'bar'"
                            record="__comp__.props.record"
                            fieldInfo="__comp__.props.archInfo.fieldNodes['bar']"
                            readonly="__comp__.props.readonly"/>
                    </t>
                    <label>label with content</label>
                </Setting>
            </div>
        </t>
    `;
    expect(compileTemplate(arch)).toHaveOuterHTML(expected);
});

test("properly compile empty ButtonBox", () => {
    const arch = /*xml*/ `
        <form>
            <sheet>
                <div class="oe_button_box" name="button_box">
                </div>
            </sheet>
        </form>
    `;
    const expected = /*xml*/ `
        <t t-translation="off">
            <div class="o_form_renderer" t-att-class="__comp__.props.class" t-attf-class="{{__comp__.props.record.isInEdition ? 'o_form_editable' : 'o_form_readonly'}} d-flex d-print-block {{ __comp__.uiService.size &lt; 5 ? &quot;flex-column&quot; : &quot;flex-nowrap h-100&quot; }} {{ __comp__.props.record.dirty ? 'o_form_dirty' : !__comp__.props.record.isNew ? 'o_form_saved' : '' }}" t-ref="compiled_view_root">
                <div t-on-scroll="__comp__.onScrollThrottled" class="o_form_sheet_bg">
                    <div class="o_form_sheet position-relative">
                        <div class="oe_button_box" name="button_box">
                        </div>
                    </div>
                </div>
            </div>
        </t>
    `;
    expect(compileTemplate(arch)).toHaveOuterHTML(expected);
});

test("invisible is correctly computed with another t-if", () => {
    patchWithCleanup(FormCompiler.prototype, {
        setup() {
            super.setup();
            this.compilers.push({
                selector: "myNode",
                fn: () => {
                    const div = createElement("div");
                    div.className = "myNode";
                    div.setAttribute("t-if", "myCondition or myOtherCondition");
                    return div;
                },
            });
        },
    });

    const arch = `<myNode invisible="field == 'value'"/>`;
    const expected = `<t t-translation="off"><div class="myNode" t-if="( myCondition or myOtherCondition ) and !__comp__.evaluateBooleanExpr(&quot;field == 'value'&quot;,__comp__.props.record.evalContextWithVirtualIds)" t-ref="compiled_view_root"/></t>`;
    expect(compileTemplate(arch)).toHaveOuterHTML(expected);
});

test("keep nosheet style if a sheet is part of a nested form", () => {
    const arch = `
        <form>
            <field name="move_line_ids" field_id="move_line_ids">
                <form>
                    <sheet/>
                </form>
            </field>
        </form>`;

    const expected = `<t t-translation="off">
        <div
            class="o_form_renderer o_form_nosheet"
            t-att-class="__comp__.props.class"
            t-attf-class="{{__comp__.props.record.isInEdition ? 'o_form_editable' : 'o_form_readonly'}} d-block {{ __comp__.props.record.dirty ? 'o_form_dirty' : !__comp__.props.record.isNew ? 'o_form_saved' : '' }}"
            t-ref="compiled_view_root"
        >
            <Field
                id="'move_line_ids'"
                name="'move_line_ids'"
                record="__comp__.props.record"
                fieldInfo="__comp__.props.archInfo.fieldNodes['move_line_ids']"
                readonly="__comp__.props.readonly"
            />
        </div>
    </t>`;
    expect(compileTemplate(arch)).toHaveOuterHTML(expected);
});

test("form with t-translation directive", () => {
    patchWithCleanup(console, { warn: (message) => expect.step(message) });
    const arch = `
        <form>
            <div t-translation="off">Hello</div>
        </form>`;

    const expected = `<t t-translation="off">
        <div
            class="o_form_renderer o_form_nosheet"
            t-att-class="__comp__.props.class"
            t-attf-class="{{__comp__.props.record.isInEdition ? 'o_form_editable' : 'o_form_readonly'}} d-block {{ __comp__.props.record.dirty ? 'o_form_dirty' : !__comp__.props.record.isNew ? 'o_form_saved' : '' }}"
            t-ref="compiled_view_root">
                <div> Hello </div>
        </div>
    </t>`;
    expect(compileTemplate(arch)).toHaveOuterHTML(expected);
    expect.verifySteps([]); // should no log any warning
});
