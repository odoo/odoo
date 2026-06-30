/** @odoo-module **/

import { KanbanArchParser } from "@web/views/kanban/kanban_arch_parser";
import { parseXML } from "@web/core/utils/xml";

function parseArch(arch, options = {}) {
    const parser = new KanbanArchParser();
    const xmlDoc = parseXML(arch);
    return parser.parse(xmlDoc, { fake: {name: { string: "Name", type: "char" },} }, "fake");
}
QUnit.module("KanbanView - ArchParser");

QUnit.test("oe_kanban_colorpicker in kanban-menu and kanban-box", (assert) => {
    const archInfo = parseArch(`
            <kanban>
                <templates>
                    <t t-name="kanban-menu">
                        <ul class="oe_kanban_colorpicker" data-field="kanban_menu_colorpicker" role="menu"/>
                    </t>
                    <t t-name="kanban-box"/>
                </templates>
            </kanban>
        `);
    assert.strictEqual(archInfo.colorField, "kanban_menu_colorpicker", "colorField should be 'kanban_menu_colorpicker'");
    const archInfo_1 = parseArch(`
        <kanban>
            <templates>
                <t t-name="kanban-menu"/>
                <t t-name="kanban-box">
                    <ul class="oe_kanban_colorpicker" data-field="kanban_box_color" role="menu"/>
                </t>
            </templates>
        </kanban>
    `);
    assert.strictEqual(archInfo_1.colorField, "kanban_box_color", "colorField should be 'kanban_box_color'");
});
