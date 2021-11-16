/** @odoo-module **/
import { makeView } from "../helpers";
import { setupControlPanelServiceRegistry } from "../../search/helpers";
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

QUnit.module("Form Compiler", (hooks) => {
    QUnit.test("properly compile simple div", async (assert) => {
        const arch = /*xml*/ `<form><div>lol</div></form>`;
        const expected = /*xml*/ `
            <t>
                <div t-attf-class="{{props.readonly ? 'o_form_readonly' : 'o_form_editable'}}" class="o_form_nosheet">
                    <div>lol</div>
                </div>
            </t>`;

        assert.areEquivalent(compileTemplate(arch), expected);
    });

    QUnit.test("properly compile simple div with field", async (assert) => {
        const arch = /*xml*/ `<form><div class="someClass">lol<field name="display_name"/></div></form>`;
        const expected = /*xml*/ `
            <t>
                <div t-attf-class="{{props.readonly ? 'o_form_readonly' : 'o_form_editable'}}" class="o_form_nosheet">
                    <div class="someClass">
                        lol
                        <Field id="&quot;field_display_name_0&quot;" name="&quot;display_name&quot;" record="record" archs="&quot;views&quot; in props.fields.display_name and props.fields.display_name.views" t-att-class="{   o_readonly_modifier: false , o_required_modifier: false , o_field_empty: isFieldEmpty(record,&quot;display_name&quot;, &quot;null&quot;) }" readonly="false or null === 'readonly' or isFieldReadonly(record,&quot;display_name&quot;,&quot;null&quot;,props.readonly)"/>
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
            <div class="o_group">
                <table class="o_group o_inner_group o_group_col_6">
                    <tbody>
                        <tr>
                            <td class="o_td_label">
                                <label class="o_form_label" for="field_display_name_0" t-esc="record.fields.display_name.string" t-att-class="{   o_readonly_modifier: false , o_required_modifier: false , o_form_label_empty: isFieldEmpty(record,&quot;display_name&quot;, &quot;null&quot;) }"/>
                            </td>
                            <td style="width: 100%">
                                <Field id="&quot;field_display_name_0&quot;" name="&quot;display_name&quot;" record="record" archs="&quot;views&quot; in props.fields.display_name and props.fields.display_name.views" t-att-class="{   o_readonly_modifier: false , o_required_modifier: false , o_field_empty: isFieldEmpty(record,&quot;display_name&quot;, &quot;null&quot;) }" readonly="false or null === 'readonly' or isFieldReadonly(record,&quot;display_name&quot;,&quot;null&quot;,props.readonly)"/>
                            </td>
                        </tr>
                    </tbody>
                </table>
                <table class="o_group o_inner_group o_group_col_6">
                    <tbody>
                        <tr>
                            <td class="o_td_label">
                                <label class="o_form_label" for="field_charfield_1" t-esc="record.fields.charfield.string" t-att-class="{   o_readonly_modifier: false , o_required_modifier: false , o_form_label_empty: isFieldEmpty(record,&quot;charfield&quot;, &quot;null&quot;) }"/>
                            </td>
                            <td style="width: 100%">
                                <Field id="&quot;field_charfield_1&quot;" name="&quot;charfield&quot;" record="record" archs="&quot;views&quot; in props.fields.charfield and props.fields.charfield.views" t-att-class="{   o_readonly_modifier: false , o_required_modifier: false , o_field_empty: isFieldEmpty(record,&quot;charfield&quot;, &quot;null&quot;) }" readonly="false or null === 'readonly' or isFieldReadonly(record,&quot;charfield&quot;,&quot;null&quot;,props.readonly)"/>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>`;

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
        <div class="o_notebook">
            <t t-set="notebook_0" t-value="state.notebook_0 or getActivePage(record, {&quot;page_1&quot;:false,&quot;page_3&quot;:false})"/>
            <div class="o_notebook_headers">
                <ul class="nav nav-tabs">
                    <li class="nav-item">
                        <a t-on-click.prevent="state.notebook_0 = &quot;page_1&quot;" href="#" class="nav-link" role="tab" t-attf-class="{{ notebook_0 === &quot;page_1&quot; ? 'active' : '' }}">
                            Page1
                        </a>
                    </li>
                    <li class="nav-item">
                        <a t-on-click.prevent="state.notebook_0 = &quot;page_3&quot;" href="#" class="nav-link" role="tab" t-attf-class="{{ notebook_0 === &quot;page_3&quot; ? 'active' : '' }}">
                            Page2
                        </a>
                    </li>
                </ul>
            </div>
            <div class="tab-content">
                <div t-if="notebook_0 === &quot;page_1&quot;" class="tab-pane active">
                    <Field id="&quot;field_charfield_2&quot;" name="&quot;charfield&quot;" record="record" archs="&quot;views&quot; in props.fields.charfield and props.fields.charfield.views" t-att-class="{   o_readonly_modifier: false , o_required_modifier: false , o_field_empty: isFieldEmpty(record,&quot;charfield&quot;, &quot;null&quot;) }" readonly="false or null === 'readonly' or isFieldReadonly(record,&quot;charfield&quot;,&quot;null&quot;,props.readonly)"/>
                </div>
                <div t-if="notebook_0 === &quot;page_3&quot;" class="tab-pane active">
                    <Field id="&quot;field_display_name_4&quot;" name="&quot;display_name&quot;" record="record" archs="&quot;views&quot; in props.fields.display_name and props.fields.display_name.views" t-att-class="{   o_readonly_modifier: false , o_required_modifier: false , o_field_empty: isFieldEmpty(record,&quot;display_name&quot;, &quot;null&quot;) }" readonly="false or null === 'readonly' or isFieldReadonly(record,&quot;display_name&quot;,&quot;null&quot;,props.readonly)"/>
                </div>
            </div>
        </div>`;

        assert.areContentEquivalent(compileTemplate(arch), expected);
    });

    QUnit.test("properly compile field with placeholder", async (assert) => {
        const arch = /*xml*/ `
            <form>
                <field name="display_name" placeholder="e.g. Contact's Name or //someinfo..."/>
            </form>`;

        const expected = /*xml*/ `
        <Field id="&quot;field_display_name_0&quot;" name="&quot;display_name&quot;" record="record" archs="&quot;views&quot; in props.fields.display_name and props.fields.display_name.views" t-att-class="{   o_readonly_modifier: false , o_required_modifier: false , o_field_empty: isFieldEmpty(record,&quot;display_name&quot;, &quot;null&quot;) }" readonly="false or null === 'readonly' or isFieldReadonly(record,&quot;display_name&quot;,&quot;null&quot;,props.readonly)" placeholder="&quot;e.g. Contact's Name or //someinfo...&quot;"/>
        `;

        assert.areContentEquivalent(compileTemplate(arch), expected);
    });

    QUnit.test("properly compile invisible", async (assert) => {
        const arch = /*xml*/ `
            <form>
                <field name="display_name" invisible="1"/>
                <field name="other_field" invisible="True"/>
                <div class="nothere1" invisible="true"/>
                <div class="visible1" invisible="0"/>
                <div class="visible2" invisible="False"/>
                <div class="visible3" invisible="false"/>
                <div modifiers="{\&quot;invisible\&quot;: [[\&quot;display_name\&quot;, \&quot;=\&quot;, \&quot;take\&quot;]]}"/>
            </form>`;

        const expected = /*xml*/ `
            <div class="visible1"/>
            <div class="visible2"/>
            <div class="visible3"/>
            <div t-if="!evalDomain(record,[[&quot;display_name&quot;,&quot;=&quot;,&quot;take&quot;]])"/>
        `;

        assert.areContentEquivalent(compileTemplate(arch), expected);
    });
});

QUnit.module("Form Renderer", (hooks) => {
    let serverData;

    hooks.beforeEach(() => {
        setupControlPanelServiceRegistry();
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

        const form = await makeView({
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

        const form = await makeView({
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
        CharField.template = owl.tags.xml`<div/>`;

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
