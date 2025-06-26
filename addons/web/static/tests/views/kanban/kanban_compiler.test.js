import { expect, test } from "@odoo/hoot";

import { KanbanCompiler } from "@web/views/kanban/kanban_compiler";

function compileTemplate(arch) {
    const parser = new DOMParser();
    const xml = parser.parseFromString(arch, "text/xml");
    const compiler = new KanbanCompiler({ kanban: xml.documentElement });
    return compiler.compile("kanban");
}

test("bootstrap dropdowns with kanban_ignore_dropdown class should be left as is", async () => {
    const arch = `
        <kanban>
            <templates>
                <t t-name="card">
                    <button name="dropdown" class="kanban_ignore_dropdown" type="button" data-bs-toggle="dropdown">Boostrap dropdown</button>
                    <div class="dropdown-menu kanban_ignore_dropdown" role="menu">
                        <span>Dropdown content</span>
                    </div>
                </t>
            </templates>
        </kanban>`;
    const expected = `
        <t t-translation="off">
            <kanban>
                <templates>
                    <t t-name="card">
                        <button name="dropdown" class="kanban_ignore_dropdown" type="button" data-bs-toggle="dropdown">Boostrap dropdown</button>
                        <div class="dropdown-menu kanban_ignore_dropdown" role="menu">
                            <span>Dropdown content</span>
                        </div>
                    </t>
                </templates>
            </kanban>
        </t>`;
    expect(compileTemplate(arch)).toHaveOuterHTML(expected);
});
