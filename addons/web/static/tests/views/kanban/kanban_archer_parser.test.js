import { expect, test } from "@odoo/hoot";
import { KanbanArchParser } from "@web/views/kanban/kanban_arch_parser";
import { parseXML } from "@web/core/utils/xml";

function parseArch(arch, options = {}) {
    const parser = new KanbanArchParser();
    const xmlDoc = parseXML(arch);
    return parser.parse(xmlDoc, { fake: { name: { string: "Name", type: "char" }, } }, "fake");
}


test("oe_kanban_colorpicker in kanban-menu and kanban-box", async () => {
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
    expect(archInfo.colorField).toBe("kanban_menu_colorpicker", {
        message: "colorField should be 'kanban_menu_colorpicker'",
    })
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
    expect(archInfo_1.colorField).toBe("kanban_box_color", {
        message: "colorField should be 'kanban_box_color'",
    });
})
