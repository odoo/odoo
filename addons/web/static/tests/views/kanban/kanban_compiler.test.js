import { test } from "@odoo/hoot";
import { expectMarkup } from "@web/../tests/web_test_helpers";

import { KanbanCompiler } from "@web/views/kanban/kanban_compiler";

function compileTemplate(arch) {
    const parser = new DOMParser();
    const xml = parser.parseFromString(arch, "text/xml");
    const compiler = new KanbanCompiler({ kanban: xml.documentElement });
    return compiler.compile("kanban").outerHTML;
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
    expectMarkup(compileTemplate(arch)).toBe(expected);
});
