import { expect, test } from "@odoo/hoot";

import { KanbanCompiler as KanbanCompilerLegacy } from "@web/views/kanban/kanban_compiler_legacy";

function compileTemplate(arch) {
    const parser = new DOMParser();
    const xml = parser.parseFromString(arch, "text/xml");
    const compiler = new KanbanCompilerLegacy({ kanban: xml.documentElement });
    return compiler.compile("kanban");
}

test("bootstrap dropdowns with kanban_ignore_dropdown class should be left as is", async () => {
    const arch = `
        <kanban>
            <templates>
                <t t-name="kanban-box">
                    <div>
                        <button name="dropdown" class="kanban_ignore_dropdown" type="button" data-bs-toggle="dropdown">Boostrap dropdown</button>
                        <div class="dropdown-menu kanban_ignore_dropdown" role="menu">
                            <span>Dropdown content</span>
                        </div>
                    </div>
                </t>
            </templates>
        </kanban>`;
    const expected = `
        <t t-translation="off">
            <kanban>
                <templates>
                    <t t-name="kanban-box">
                        <div>
                            <button name="dropdown" class="kanban_ignore_dropdown" type="button" data-bs-toggle="dropdown">Boostrap dropdown</button>
                            <div class="dropdown-menu kanban_ignore_dropdown" role="menu">
                                <span>Dropdown content</span>
                            </div>
                        </div>
                    </t>
                </templates>
            </kanban>
        </t>`;
    expect(compileTemplate(arch)).toHaveOuterHTML(expected);
});
