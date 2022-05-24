/** @odoo-module **/
import { makeView } from "../helpers";
import { setupViewRegistries } from "@web/../tests/views/helpers";
import { FormCompiler } from "@web/views/form/form_compiler";
import { registry } from "@web/core/registry";

function compileTemplate(arch) {
    const parser = new DOMParser();
    const xml = parser.parseFromString(arch, "text/xml");
    const compiler = new FormCompiler();
    return compiler.compile(xml.documentElement).outerHTML;
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
                <div t-attf-class="{{props.record.isInEdition ? 'o_form_editable' : 'o_form_readonly'}}" class="o_form_nosheet" t-ref="compiled_view_root">
                    <div>lol</div>
                </div>
            </t>`;

        assert.areEquivalent(compileTemplate(arch), expected);
    });

    QUnit.test("properly compile simple div with field", async (assert) => {
        const arch = /*xml*/ `<form><div class="someClass">lol<field name="display_name"/></div></form>`;
        const expected = /*xml*/ `
            <t>
                <div t-attf-class="{{props.record.isInEdition ? 'o_form_editable' : 'o_form_readonly'}}" class="o_form_nosheet" t-ref="compiled_view_root">
                    <div class="someClass">
                        lol
                        <Field id="'display_name'" name="'display_name'" record="record" fieldInfo="fieldNodes['display_name']" archs="'views' in record.fields.display_name and record.fields.display_name.views"/>
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
                     <t t-set-slot="item_0" type="'item'" sequence="0" t-slot-scope="scope" props="{id:'display_name',fieldName:'display_name',record:record,string:record.fields.display_name.string,fieldInfo:fieldNodes['display_name']}" Component="constructor.components.FormLabel" subType="'item_component'" itemSpan="2">
                        <Field id="'display_name'" name="'display_name'" record="record" fieldInfo="fieldNodes['display_name']" archs="'views' in record.fields.display_name and record.fields.display_name.views" class="scope &amp;&amp; scope.className" />
                     </t>
                  </InnerGroup>
               </t>
               <t t-set-slot="item_1" type="'item'" sequence="1" t-slot-scope="scope" itemSpan="1">
                  <InnerGroup class="scope &amp;&amp; scope.className">
                     <t t-set-slot="item_0" type="'item'" sequence="0" t-slot-scope="scope" props="{id:'charfield',fieldName:'charfield',record:record,string:record.fields.charfield.string,fieldInfo:fieldNodes['charfield']}" Component="constructor.components.FormLabel" subType="'item_component'" itemSpan="2">
                        <Field id="'charfield'" name="'charfield'" record="record" fieldInfo="fieldNodes['charfield']" archs="'views' in record.fields.charfield and record.fields.charfield.views" class="scope &amp;&amp; scope.className" />
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
                <t t-set-slot="page_1" title="&quot;Page1&quot;" isVisible="true">
                    <Field id="'charfield'" name="'charfield'" record="record" fieldInfo="fieldNodes['charfield']" archs="'views' in record.fields.charfield and record.fields.charfield.views"/>
                </t>
                <t t-set-slot="page_2" title="&quot;Page2&quot;" isVisible="true">
                    <Field id="'display_name'" name="'display_name'" record="record" fieldInfo="fieldNodes['display_name']" archs="'views' in record.fields.display_name and record.fields.display_name.views"/>
               </t>
           </Notebook>`;

        assert.areContentEquivalent(compileTemplate(arch), expected);
    });

    QUnit.test("properly compile field with placeholder", async (assert) => {
        const arch = /*xml*/ `
            <form>
                <field name="display_name" placeholder="e.g. Contact's Name or //someinfo..."/>
            </form>`;

        const expected = /*xml*/ `
            <Field id="'display_name'" name="'display_name'" record="record" fieldInfo="fieldNodes['display_name']" archs="'views' in record.fields.display_name and record.fields.display_name.views" placeholder="'e.g. Contact\\'s Name or //someinfo...'"/>
        `;

        assert.areContentEquivalent(compileTemplate(arch), expected);
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
            <div t-if="!evalDomain(record,[[&quot;display_name&quot;,&quot;=&quot;,&quot;take&quot;]])" />
        `;

        assert.areContentEquivalent(compileTemplate(arch), expected);
    });
});

QUnit.module("Form Renderer", (hooks) => {
    let serverData;

    hooks.beforeEach(() => {
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
});
