/** @odoo-module **/
import { KanbanCompiler } from "@web/views/kanban/kanban_compiler";
import { registry } from "@web/core/registry";
import { makeFakeLocalizationService } from "@web/../tests/helpers/mock_services";

function compileTemplate(arch) {
    const parser = new DOMParser();
    const xml = parser.parseFromString(arch, "text/xml");
    const compiler = new KanbanCompiler({ kanban: xml.documentElement });
    return compiler.compile("kanban").outerHTML;
}

function assertTemplatesEqual(template1, template2) {
    if (template1.replace(/\s/g, "") === template2.replace(/\s/g, "")) {
        QUnit.assert.ok(true);
    } else {
        QUnit.assert.strictEqual(template1, template2);
    }
}

QUnit.module("Kanban Compiler", (hooks) => {
    hooks.beforeEach(() => {
        // compiler generates a piece of template for the translate alert in multilang
        registry.category("services").add("localization", makeFakeLocalizationService());
    });

    QUnit.test("bootstrap dropdowns with kanban_ignore_dropdown class should be left as is", async () => {
        const arch = `<kanban>
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
        const expected = `<t t-translation="off">
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
        assertTemplatesEqual(compileTemplate(arch), expected);
    });
});
