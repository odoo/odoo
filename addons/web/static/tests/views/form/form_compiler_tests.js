/** @odoo-module **/
import { makeView } from "../helpers";
import { setupViewRegistries } from "@web/../tests/views/helpers";
import { FormCompiler } from "@web/views/form/form_compiler";
import { registry } from "@web/core/registry";
import { click, getFixture, patchWithCleanup } from "../../helpers/utils";
import { createElement } from "@web/core/utils/xml";

function compileTemplate(arch) {
    const parser = new DOMParser();
    const xml = parser.parseFromString(arch, "text/xml");
    const compiler = new FormCompiler({ form: xml.documentElement });
    return compiler.compile("form").outerHTML;
}

QUnit.assert.areEquivalent = function (template1, template2) {
    if (template1.replace(/\s/g, "") === template2.replace(/\s/g, "")) {
        QUnit.assert.ok(true);
    } else {
        QUnit.assert.strictEqual(template1, template2);
    }
};

QUnit.assert.areContentEquivalent = function (template, content) {
    const parser = new DOMParser();
    const doc = parser.parseFromString(template, "text/xml");
    const templateContent = doc.documentElement.firstChild.innerHTML;
    QUnit.assert.areEquivalent(templateContent, content);
};

QUnit.module("Form Compiler", () => {
    QUnit.test("properly compile simple div", async (assert) => {
        const arch = /*xml*/ `<form><div>lol</div></form>`;
        const expected = /*xml*/ `
            <t>
                <div t-att-class="props.class" t-attf-class="{{props.record.isInEdition ? 'o_form_editable' : 'o_form_readonly'}} d-block" class="o_form_nosheet" t-ref="compiled_view_root">
                    <div>lol</div>
                </div>
            </t>`;

        assert.areEquivalent(compileTemplate(arch), expected);
    });

    QUnit.test("label with empty string is not rendered", async (assert) => {
        const arch = /*xml*/ `<form><field name="test"/><label for="test" string=""/></form>`;
        const expected = /*xml*/ `
            <t>
                <div t-att-class="props.class" t-attf-class="{{props.record.isInEdition ? 'o_form_editable' : 'o_form_readonly'}} d-block" class="o_form_nosheet" t-ref="compiled_view_root">
                    <Field id="'test'" name="'test'" record="props.record" fieldInfo="props.archInfo.fieldNodes['test']"/>
                </div>
            </t>`;
        assert.areEquivalent(compileTemplate(arch), expected);
    });

    QUnit.test("properly compile simple div with field", async (assert) => {
        const arch = /*xml*/ `<form><div class="someClass">lol<field name="display_name"/></div></form>`;
        const expected = /*xml*/ `
            <t>
                <div t-att-class="props.class" t-attf-class="{{props.record.isInEdition ? 'o_form_editable' : 'o_form_readonly'}} d-block" class="o_form_nosheet" t-ref="compiled_view_root">
                    <div class="someClass">
                        lol
                        <Field id="'display_name'" name="'display_name'" record="props.record" fieldInfo="props.archInfo.fieldNodes['display_name']"/>
                    </div>
                </div>
            </t>`;

        assert.areEquivalent(compileTemplate(arch), expected);
    });

    QUnit.test("properly compile inner groups", async (assert) => {
        const arch = /*xml*/ `
            <form>
                <group>
                    <group><field name="display_name"/></group>
                    <group><field name="charfield"/></group>
                </group>
            </form>`;
        const expected = /*xml*/ `
            <OuterGroup>
               <t t-set-slot="item_0" type="'item'" sequence="0" t-slot-scope="scope" itemSpan="1">
                  <InnerGroup class="scope &amp;&amp; scope.className">
                     <t t-set-slot="item_0" type="'item'" sequence="0" t-slot-scope="scope" props="{id:'display_name',fieldName:'display_name',record:props.record,string:props.record.fields.display_name.string,fieldInfo:props.archInfo.fieldNodes['display_name']}" Component="constructor.components.FormLabel" subType="'item_component'" itemSpan="2">
                        <Field id="'display_name'" name="'display_name'" record="props.record" fieldInfo="props.archInfo.fieldNodes['display_name']" class="scope &amp;&amp; scope.className" />
                     </t>
                  </InnerGroup>
               </t>
               <t t-set-slot="item_1" type="'item'" sequence="1" t-slot-scope="scope" itemSpan="1">
                  <InnerGroup class="scope &amp;&amp; scope.className">
                     <t t-set-slot="item_0" type="'item'" sequence="0" t-slot-scope="scope" props="{id:'charfield',fieldName:'charfield',record:props.record,string:props.record.fields.charfield.string,fieldInfo:props.archInfo.fieldNodes['charfield']}" Component="constructor.components.FormLabel" subType="'item_component'" itemSpan="2">
                        <Field id="'charfield'" name="'charfield'" record="props.record" fieldInfo="props.archInfo.fieldNodes['charfield']" class="scope &amp;&amp; scope.className" />
                     </t>
                  </InnerGroup>
               </t>
            </OuterGroup>`;

        assert.areContentEquivalent(compileTemplate(arch), expected);
    });

    QUnit.test("properly compile notebook", async (assert) => {
        const arch = /*xml*/ `
                <form>
                    <notebook>
                        <page name="p1" string="Page1"><field name="charfield"/></page>
                        <page name="p2" string="Page2"><field name="display_name"/></page>
                    </notebook>
                </form>`;

        const expected = /*xml*/ `
            <Notebook>
                <t t-set-slot="page_1" title="\`Page1\`" name="\`p1\`" isVisible="true">
                    <Field id="'charfield'" name="'charfield'" record="props.record" fieldInfo="props.archInfo.fieldNodes['charfield']"/>
                </t>
                <t t-set-slot="page_2" title="\`Page2\`" name="\`p2\`" isVisible="true">
                    <Field id="'display_name'" name="'display_name'" record="props.record" fieldInfo="props.archInfo.fieldNodes['display_name']"/>
               </t>
           </Notebook>`;

        assert.areContentEquivalent(compileTemplate(arch), expected);
    });

    QUnit.test("properly compile field without placeholder", async (assert) => {
        const arch = /*xml*/ `
            <form>
                <field name="display_name" placeholder="e.g. Contact's Name or //someinfo..."/>
            </form>`;

        const expected = /*xml*/ `
            <Field id="'display_name'" name="'display_name'" record="props.record" fieldInfo="props.archInfo.fieldNodes['display_name']"/>
        `;

        assert.areContentEquivalent(compileTemplate(arch), expected);
    });

    QUnit.test("properly compile no sheet", async (assert) => {
        const arch = /*xml*/ `
            <form>
            <header>someHeader</header>
            <div>someDiv</div>
            </form>`;

        const expected = /*xml*/ `
            <t>
            <div t-att-class="props.class" t-attf-class="{{props.record.isInEdition ? 'o_form_editable' : 'o_form_readonly'}} d-block" class="o_form_nosheet" t-ref="compiled_view_root">
                <div class="o_form_statusbar"><StatusBarButtons readonly="!props.record.isInEdition"/></div>
                <div>someDiv</div>
            </div>
            </t>`;

        assert.areEquivalent(compileTemplate(arch), expected);
    });

    QUnit.test("properly compile sheet", async (assert) => {
        const arch = /*xml*/ `
            <form>
            <header>someHeader</header>
            <div>someDiv</div>
            <sheet>
                <div>inside sheet</div>
            </sheet>
            <div>after sheet</div>
            </form>`;

        const expected = /*xml*/ `
            <t>
            <div t-att-class="props.class" t-attf-class="{{props.record.isInEdition ? 'o_form_editable' : 'o_form_readonly'}} d-flex {{ uiService.size &lt; 6 ? &quot;flex-column&quot; : &quot;flex-nowrap h-100&quot; }}" t-ref="compiled_view_root">
                <div class="o_form_sheet_bg">
                    <div class="o_form_statusbar"><StatusBarButtons readonly="!props.record.isInEdition"/></div>
                    <div>someDiv</div>
                    <div class="o_form_sheet position-relative">
                        <div>inside sheet</div>
                    </div>
                </div>
                <div>after sheet</div>
            </div>
            </t>
        `;

        assert.areEquivalent(compileTemplate(arch), expected);
    });

    QUnit.test("properly compile invisible", async (assert) => {
        // cf python side: def transfer_node_to_modifiers
        // modifiers' string are evaluated to their boolean or array form
        // So the following arch may actually be written as:
        // ```<form>
        //      <field name="display_name" invisible="1" />
        //      <div class="visible3" invisible="0"/>
        //      <div modifiers="{'invisible': [['display_name', '=', 'take']]}"/>
        //    </form>````
        const arch = /*xml*/ `
            <form>
                <field name="display_name" modifiers="{&quot;invisible&quot;: true}" />
                <div class="visible3" modifiers="{&quot;invisible&quot;: false}"/>
                <div modifiers="{&quot;invisible&quot;: [[&quot;display_name&quot;, &quot;=&quot;, &quot;take&quot;]]}"/>
            </form>`;

        const expected = /*xml*/ `
            <div class="visible3" />
            <div t-if="!evalDomainFromRecord(props.record,[[&quot;display_name&quot;,&quot;=&quot;,&quot;take&quot;]])" />
        `;

        assert.areContentEquivalent(compileTemplate(arch), expected);
    });

    QUnit.test("compile invisible containing string as domain", async (assert) => {
        const arch = /*xml*/ `
            <form>
                <field name="display_name" modifiers="{&quot;invisible&quot;: true}" />
                <div class="visible3" modifiers="{&quot;invisible&quot;: false}"/>
                <div modifiers="{&quot;invisible&quot;: &quot;[['display_name', '=', 'take']]&quot;}"/>
            </form>`;

        const expected = /*xml*/ `
            <div class="visible3" />
            <div t-if="!evalDomainFromRecord(props.record,&quot;[['display_name','=','take']]&quot;)" />
        `;
        assert.areContentEquivalent(compileTemplate(arch), expected);
    });

    QUnit.test("properly compile status bar with content", (assert) => {
        const arch = /*xml*/ `
            <form>
            <header><div>someDiv</div></header>
            </form>`;

        const expected = /*xml*/ `
            <div class="o_form_statusbar">
               <StatusBarButtons readonly="!props.record.isInEdition">
                  <t t-set-slot="button_0" isVisible="true" displayInReadOnly="false">
                     <div>someDiv</div>
                  </t>
               </StatusBarButtons>
            </div>`;

        assert.areContentEquivalent(compileTemplate(arch), expected);
    });

    QUnit.test("properly compile status bar without content", (assert) => {
        const arch = /*xml*/ `
            <form>
            <header></header>
            </form>`;

        const expected = /*xml*/ `
            <div class="o_form_statusbar">
               <StatusBarButtons readonly="!props.record.isInEdition"/>
            </div>`;

        assert.areContentEquivalent(compileTemplate(arch), expected);
    });
});

QUnit.module("Form Renderer", (hooks) => {
    let target, serverData;

    hooks.beforeEach(() => {
        target = getFixture();
        setupViewRegistries();
        serverData = {
            models: {
                partner: {
                    fields: {
                        display_name: { type: "char" },
                        charfield: { type: "char" },
                    },
                    records: [
                        { id: 1, display_name: "firstRecord", charfield: "content of charfield" },
                    ],
                },
            },
        };
    });

    QUnit.test("compile form with modifiers and attrs - string as domain", async (assert) => {
        serverData.views = {
            "partner,1,form": /*xml*/ `
                <form>
                    <div modifiers="{&quot;invisible&quot;: &quot;[['display_name', '=', uid]]&quot;}">
                        <field name="charfield"/>
                    </div>
                    <field name="display_name" attrs="{'readonly': &quot;[['display_name', '=', uid]]&quot;}"/>
                </form>`,
        };

        await makeView({
            serverData,
            resModel: "partner",
            type: "form",
            resId: 1,
        });

        await click(target.querySelector(".o_form_button_edit"));
        assert.containsN(target, ".o_form_editable input", 2);
    });

    QUnit.test("compile notebook with modifiers", async (assert) => {
        assert.expect(0);

        serverData.views = {
            "partner,1,form": /*xml*/ `
                <form>
                    <sheet>
                        <notebook>
                            <page name="p1" attrs="{'invisible': [['display_name', '=', 'lol']]}"><field name="charfield"/></page>
                            <page name="p2"><field name="display_name"/></page>
                        </notebook>
                    </sheet>
                </form>`,
        };

        await makeView({
            serverData,
            resModel: "partner",
            type: "form",
            resId: 1,
        });
    });

    QUnit.test("compile header and buttons", async (assert) => {
        assert.expect(0);

        serverData.views = {
            "partner,1,form": /*xml*/ `
                <form>
                    <header>
                         <button string="ActionButton" class="oe_highlight" name="action_button" type="object"/>
                     </header>
                </form>`,
        };

        await makeView({
            serverData,
            resModel: "partner",
            type: "form",
            resId: 1,
        });
    });

    QUnit.test("render field with placeholder", async (assert) => {
        assert.expect(1);

        class CharField extends owl.Component {
            setup() {
                assert.strictEqual(this.props.placeholder, "e.g. Contact's Name or //someinfo...");
            }
        }
        CharField.template = owl.xml`<div/>`;
        CharField.extractProps = ({ attrs }) => ({ placeholder: attrs.placeholder });

        registry.category("fields").add("char", CharField, { force: true });

        serverData.views = {
            "partner,1,form": /*xml*/ `
                <form>
                    <field name="display_name" placeholder="e.g. Contact's Name or //someinfo..." />
                </form>`,
        };

        await makeView({
            serverData,
            resModel: "partner",
            type: "form",
            resId: 1,
        });
    });

    QUnit.test("compile a button with id", async (assert) => {
        serverData.views = {
            "partner,1,form": /*xml*/ `
                <form>
                    <header>
                         <button id="action_button" string="ActionButton"/>
                     </header>
                </form>`,
        };

        await makeView({
            serverData,
            resModel: "partner",
            type: "form",
            resId: 1,
        });

        assert.containsOnce(target, "button[id=action_button]");
    });

    QUnit.test("invisible is correctly computed with another t-if", (assert) => {
        patchWithCleanup(FormCompiler.prototype, {
            setup() {
                this._super();
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

        const arch = `<myNode modifiers="{&quot;invisible&quot;: [[&quot;field&quot;, &quot;=&quot;, &quot;value&quot;]]}" />`;

        const expected = `<t><div class="myNode" t-if="( myCondition or myOtherCondition ) and !evalDomainFromRecord(props.record,[[&quot;field&quot;,&quot;=&quot;,&quot;value&quot;]])" t-ref="compiled_view_root"/></t>`;
        assert.areEquivalent(compileTemplate(arch), expected);
    });
});
