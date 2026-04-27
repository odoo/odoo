import { expect, test } from "@odoo/hoot";
import { animationFrame, Deferred } from "@odoo/hoot-dom";
import { onMounted } from "@odoo/owl";
import {
    contains,
    defineModels,
    fields,
    models,
    onRpc,
    patchWithCleanup,
    serverState,
} from "@web/../tests/web_test_helpers";
import { CodeEditor } from "@web/core/code_editor/code_editor";

import {
    disableHookAnimation,
    editView,
    mountViewEditor,
} from "@web_studio/../tests/view_editor_tests_utils";

class Coucou extends models.Model {
    display_name = fields.Char();
    m2o = fields.Many2one({ relation: "product" });
    char_field = fields.Char();
    priority = fields.Selection({
        selection: [
            ["1", "Low"],
            ["2", "Medium"],
            ["3", "High"],
        ],
    });

    _records = [];
}

class Partner extends models.Model {
    display_name = fields.Char();
    image = fields.Binary();

    _records = [
        {
            id: 1,
            display_name: "jean",
        },
    ];
}

class Product extends models.Model {
    display_name = fields.Char();

    _records = [{ id: 1, display_name: "A very good product" }];
}

defineModels([Coucou, Product, Partner]);

test("template without t-name='card' load the legacy kanban editor", async () => {
    // avoid "kanban-box" deprecation warnings in this suite, which
    // defines legacy kanban on purpose
    const originalConsoleWarn = console.warn;
    patchWithCleanup(console, {
        warn: (msg) => {
            if (msg !== "'kanban-box' is deprecated, define a 'card' template instead") {
                originalConsoleWarn(msg);
            }
        },
    });
    await mountViewEditor({
        type: "kanban",
        resModel: "coucou",
        arch: `<kanban>
        <templates>
            <t t-name="kanban-box">
                <div>
                    <field name="char_field"/>
                </div>
            </t>
        </templates>
    </kanban>
    `,
    });
    expect(".o_web_studio_kanban_view_editor_legacy").toHaveCount(1);
    expect(".o_kanban_record .o_web_studio_kanban_hook").toHaveCount(4, {
        message: "hooks are present inside the card",
    });
});

test("empty kanban editor", async () => {
    await mountViewEditor({
        type: "kanban",
        resModel: "coucou",
        arch: `<kanban>
        <templates>
            <t t-name="card">
            </t>
        </templates>
    </kanban>
    `,
    });
    expect(".o_kanban_renderer").toHaveCount(1);
});

test("templates without a main node are wrapped in a main node by the editor", async () => {
    await mountViewEditor({
        type: "kanban",
        resModel: "coucou",
        arch: `<kanban>
        <templates>
            <t t-name="card">
                <field name="char_field"/>
            </t>
        </templates>
    </kanban>
    `,
    });
    expect("article.o_kanban_record > main").toHaveCount(1);
    expect("article.o_kanban_record > main").toHaveAttribute("studioxpath", null, {
        message: "no xpath is set on this element has it doesn't exist in the original template",
    });
    expect("article.o_kanban_record > .o_web_studio_hook[data-type=kanbanAsideHook]").toHaveCount(
        2,
        {
            message: "hooks are present around the element to drop an aside",
        }
    );
});

test("kanban structures display depends if element is present in the view", async () => {
    onRpc("/web_studio/edit_view", (request) => {
        // in this test, we result with a completely different template
        const newArch = `
                <kanban>
                    <templates>
                        <t t-name="card">
                            <widget name="web_ribbon" title="Ribbon"/>
                            <aside>
                            </aside>
                            <main>
                                <field name="char_field"/>
                            </main>
                        </t>
                    </templates>
                </kanban>
            `;
        return editView(request, "kanban", newArch);
    });
    await mountViewEditor({
        type: "kanban",
        resModel: "coucou",
        arch: `<kanban>
            <templates>
                <t t-name="card">
                    <field name="char_field"/>
                </t>
                <t t-name="menu">
                    <a>Item</a>
                </t>
            </templates>
        </kanban>
    `,
    });
    await contains(".o_web_studio_new").click();
    expect(".o_web_studio_field_menu").toHaveCount(0);
    expect(".o_web_studio_field_aside").toHaveCount(1);
    expect(".o_web_studio_field_footer").toHaveCount(1);
    expect(".o_web_studio_field_ribbon").toHaveCount(1);
    await contains(".o_web_studio_new_components .o_web_studio_field_aside").dragAndDrop(
        ".o_web_studio_hook[data-type=kanbanAsideHook]"
    );
    await contains(".o_web_studio_new").click();
    expect(".o_web_studio_field_menu").toHaveCount(1);
    expect(".o_web_studio_field_aside").toHaveCount(0);
    expect(".o_web_studio_field_footer").toHaveCount(1);
    expect(".o_web_studio_field_ribbon").toHaveCount(0);
});

test("hooks are placed inline around fields displayed in a span", async () => {
    await mountViewEditor({
        type: "kanban",
        resModel: "coucou",
        arch: `<kanban>
        <templates>
            <t t-name="card">
                <main>
                    <h3>Card</h3>
                    <div class="inline">
                        <field name="display_name"/>,
                        <field name="char_field"/>
                    </div>
                    <div class="block">
                        <field name="display_name" widget="char"/>,
                        <field name="char_field" widget="char"/>
                    </div>
                </main>
            </t>
        </templates>
    </kanban>
    `,
    });
    expect("article.o_kanban_record > main").toHaveCount(1);
    expect(".inline span.o_web_studio_hook[data-type=field]").toHaveCount(4, {
        message: "hooks are using a span instead of a div",
    });
    expect(".block div.o_web_studio_hook[data-type=field]").toHaveCount(4, {
        message: "hooks are using a div around field components",
    });
});

test("card without main should be able to add a footer", async () => {
    await mountViewEditor({
        type: "kanban",
        resModel: "coucou",
        arch: `<kanban>
        <templates>
            <t t-name="card">
                <h3>Card</h3>
                <div class="inline">
                    <field name="display_name"/>,
                    <field name="char_field"/>
                </div>
            </t>
        </templates>
    </kanban>
    `,
    });
    expect("main .o_web_studio_hook[data-structures=footer]").toHaveCount(1);
});

test("adding an aside element calls the right operation", async () => {
    onRpc("/web_studio/edit_view", async (request) => {
        const { params } = await request.json();
        expect(params.operations[0].type).toBe("kanban_wrap_main");
        // server side, this operation would wrap the content inside a <main> node
        const newArch = `
                <kanban>
                    <templates>
                        <t t-name="card">
                            <main>
                                <t>
                                    <h3>Card</h3>
                                    <div class="inline">
                                        <field name="display_name"/>,
                                        <field name="char_field"/>
                                    </div>
                                </t>
                            </main>
                        </t>
                    </templates>
                </kanban>
            `;
        return editView(params, "kanban", newArch);
    });
    await mountViewEditor({
        type: "kanban",
        resModel: "coucou",
        arch: `<kanban>
        <templates>
            <t t-name="card">
                <h3>Card</h3>
            </t>
        </templates>
    </kanban>
    `,
    });
    await contains(".o_web_studio_new").click();
    await contains(".o_web_studio_new_components .o_web_studio_field_aside").dragAndDrop(
        ".o_web_studio_hook[data-type=kanbanAsideHook]"
    );
});

test("adding a footer element calls the right operation", async () => {
    onRpc("/web_studio/edit_view", async (request) => {
        const { params } = await request.json();
        expect(params.operations[0].type).toBe("kanban_wrap_main");
        // server side, this operation would wrap the content inside a <main> node
        const newArch = `
                <kanban>
                    <templates>
                        <t t-name="card">
                            <main>
                                <t>
                                    <h3>Card</h3>
                                </t>
                            </main>
                        </t>
                    </templates>
                </kanban>
            `;
        return editView(params, "kanban", newArch);
    });
    await mountViewEditor({
        type: "kanban",
        resModel: "coucou",
        arch: `<kanban>
        <templates>
            <t t-name="card">
                <h3>Card</h3>
            </t>
        </templates>
    </kanban>
    `,
    });
    await contains(".o_web_studio_new").click();
    await contains(".o_web_studio_new_components .o_web_studio_field_footer").dragAndDrop(
        ".o_web_studio_hook[data-type=footer]"
    );
});

test("adding a menu element calls the right operation", async () => {
    onRpc("/web_studio/edit_view", async (request) => {
        const { params } = await request.json();
        expect(params.operations[0].type).toBe("kanban_menu");
    });
    await mountViewEditor({
        type: "kanban",
        resModel: "coucou",
        arch: `<kanban>
        <templates>
            <t t-name="card">
                <h3>Card</h3>
            </t>
        </templates>
    </kanban>
    `,
    });
    disableHookAnimation();
    await contains(".o_web_studio_new").click();
    const { drop, moveTo } = await contains(
        ".o_web_studio_new_components .o_web_studio_field_menu"
    ).drag();
    await animationFrame();
    await moveTo(".o_web_studio_hook[data-type=t]");
    expect(".o_web_studio_hook[data-type=t]").toHaveClass("o_web_studio_hook_visible");
    await drop();
});

test("adding a colorpicker inside the menu", async () => {
    onRpc("/web_studio/edit_view", async (request) => {
        const { params } = await request.json();
        expect(params.operations[0].type).toBe("kanban_colorpicker");

        Coucou._fields.x_color = fields.Integer({
            string: "Color",
        });
        const newArch = `
                    <kanban>
                        <templates>
                            <t t-name="card">
                                <h3>Card</h3>
                            </t>
                            <t t-name="menu">
                                <small>Menu</small>
                                <field name="x_color" widget="kanban_color_picker" />
                            </t>
                        </templates>
                    </kanban>
                `;
        return editView(params, "kanban", newArch);
    });
    await mountViewEditor({
        type: "kanban",
        resModel: "coucou",
        arch: `<kanban>
        <templates>
            <t t-name="card">
                <h3>Card</h3>
            </t>
            <t t-name="menu">
                <small>Menu</small>
            </t>
        </templates>
    </kanban>
    `,
    });
    disableHookAnimation();
    await contains(".o_web_studio_new").click();
    const { drop, moveTo } = await contains(
        ".o_web_studio_new_components .o_web_studio_field_color_picker"
    ).drag();
    await animationFrame();
    await moveTo(".o_web_studio_hook[data-type=t]");
    expect(".o_web_studio_hook[data-type=t]").toHaveClass("o_web_studio_hook_visible");
    await drop();
    expect(".o_dropdown_kanban").toHaveCount(1);
    await contains(".o_dropdown_kanban").click();
    expect(".o_notebook_content h3").toHaveText("Menu");
    await contains(".o_notebook_content .btn-secondary:contains(Color Picker)").click();
    expect(".o_notebook_content h3").toHaveText("Field", {
        message: "it is possible to edit the field with kanban_color_picker widget",
    });
});

test("adding a colorpicker when menu is not present", async () => {
    onRpc("/web_studio/edit_view", async (request) => {
        const { params } = await request.json();
        expect(params.operations[0].type).toBe("kanban_menu");
        expect(params.operations[1].type).toBe("kanban_colorpicker");
        Coucou._fields.x_color = fields.Integer({
            string: "Color",
        });
        const newArch = `
                    <kanban>
                        <templates>
                            <t t-name="card">
                                <h3>Card</h3>
                            </t>
                            <t t-name="menu">
                                <field name="x_color" widget="kanban_color_picker" />
                            </t>
                        </templates>
                    </kanban>
                `;
        return editView(params, "kanban", newArch);
    });
    await mountViewEditor({
        type: "kanban",
        resModel: "coucou",
        arch: `<kanban>
        <templates>
            <t t-name="card">
                <h3>Card</h3>
            </t>
        </templates>
    </kanban>
    `,
    });
    disableHookAnimation();
    await contains(".o_web_studio_new").click();
    const { drop, moveTo } = await contains(
        ".o_web_studio_new_components .o_web_studio_field_color_picker"
    ).drag();
    await animationFrame();
    await moveTo(".o_web_studio_hook[data-type=t]");
    expect(".o_web_studio_hook[data-type=t]").toHaveClass("o_web_studio_hook_visible");
    await drop();
    expect(".o_dropdown_kanban").toHaveCount(1);
    await contains(".o_dropdown_kanban").click();
    expect(".o_notebook_content h3").toHaveText("Menu");
    await contains(".o_notebook_content .btn-secondary:contains(Color Picker)").click();
    expect(".o_notebook_content h3").toHaveText("Field", {
        message: "it is possible to edit the field with kanban_color_picker widget",
    });
});

test("can_open attribute can be edited from the sidebar", async () => {
    onRpc("/web_studio/edit_view", async (request) => {
        const { params } = await request.json();
        expect(params.operations[0].new_attrs.can_open).toBe(false);
        const newArch = `
            <kanban can_open="false">
                <templates>
                    <t t-name="card">
                        <h3>Card</h3>
                    </t>
                </templates>
            </kanban>
        `;
        return editView(params, "kanban", newArch);
    });
    await mountViewEditor({
        type: "kanban",
        resModel: "coucou",
        arch: `<kanban>
        <templates>
            <t t-name="card">
                <h3>Card</h3>
            </t>
        </templates>
    </kanban>
    `,
    });
    await contains(".o_web_studio_view").click();
    expect("input[id=can_open]").toHaveCount(1);
    expect("input[id=can_open]").toBeChecked({
        message: "option is checked by default when the arch does not specify",
    });
    await contains("input[id=can_open]").click();
    expect("input[id=can_open]").not.toBeChecked();
});

test("buttons can be edited when being selected", async () => {
    await mountViewEditor({
        type: "kanban",
        resModel: "coucou",
        arch: `<kanban>
        <templates>
            <t t-name="card">
                <main>
                    Coucou
                    <footer>
                        <a type="action" name="my_first_action" class="btn btn-link" role="button">
                            <i class="fa fa-recycle"/> Do something
                        </a>
                        <button type="action" name="my_last_action" class="btn btn-primary" role="button">
                            Click me
                        </button>
                    </footer>
                </main>
            </t>
        </templates>
    </kanban>
    `,
    });
    expect("footer .o-web-studio-editor--element-clickable").toHaveCount(2);
    await contains("a.o-web-studio-editor--element-clickable").click();
    expect("input[id=class]").toHaveCount(1);
    expect("input[id=name]").toHaveValue("my_first_action");
    await contains("button.o-web-studio-editor--element-clickable").click();
    expect("input[id=class]").toHaveCount(1);
    expect("input[id=name]").toHaveValue("my_last_action");
});

test("grouped kanban editor", async () => {
    onRpc("web_read_group", ({ kwargs }) => {
        expect.step("web_read_group");
        expect(kwargs.limit).toBe(1);
    });
    await mountViewEditor({
        type: "kanban",
        resModel: "coucou",
        arch: `<kanban default_group_by='display_name'>
                    <templates>
                        <t t-name='card'>
                            <field name='display_name'/>
                        </t>
                    </templates>
                </kanban>`,
    });
    expect.verifySteps(["web_read_group"]);
    expect(".o_web_studio_kanban_view_editor").toHaveClass("o_kanban_grouped");
    expect(".o_web_studio_kanban_view_editor .o_view_nocontent").toHaveCount(0);
    expect(".o_web_studio_kanban_view_editor .o-web-studio-editor--element-clickable").toHaveCount(
        1
    );
    expect(".o_web_studio_kanban_view_editor .o-web-studio-editor--element-clickable").toHaveClass(
        "o_web_studio_widget_empty"
    );
    expect(".o_web_studio_kanban_view_editor .o_web_studio_hook").toHaveCount(7);
});

test("grouped kanban editor with record", async () => {
    Coucou._records = [{ id: 1, display_name: "coucou 1" }];
    await mountViewEditor({
        type: "kanban",
        resModel: "coucou",
        arch: `<kanban default_group_by='display_name'>
                    <templates>
                        <t t-name='card'>
                            <field name='display_name'/>
                        </t>
                    </templates>
                </kanban>`,
    });
    expect(".o_web_studio_kanban_view_editor").toHaveClass("o_kanban_grouped");
    expect(".o_kanban_group .o_kanban_header").toHaveCount(2);
    expect(".o_kanban_grouped .o_kanban_header_title").toHaveText("coucou 1\n(1)");
    expect(".o_kanban_group .o_kanban_counter").toHaveCount(0);
    expect(".o_web_studio_kanban_view_editor .o-web-studio-editor--element-clickable").toHaveCount(
        1
    );
    expect(
        ".o_web_studio_kanban_view_editor .o-web-studio-editor--element-clickable"
    ).not.toHaveClass("o_web_studio_widget_empty");
    expect(".o_web_studio_kanban_view_editor .o_web_studio_hook").toHaveCount(7);
});

test("kanban editor, grouped on date field, no record", async () => {
    Coucou._fields.date = fields.Date({ string: "Date" });
    await mountViewEditor({
        type: "kanban",
        resModel: "coucou",
        arch: `<kanban default_group_by='date'>
                <templates>
                    <t t-name='card'>
                        <field name='display_name'/>
                    </t>
                </templates>
            </kanban>`,
    });
    expect(".o_web_studio_kanban_view_editor").toHaveClass("o_kanban_grouped");
    expect(".o_kanban_record:not(.o_kanban_demo)").toHaveCount(1);
});

test("kanban editor, grouped on date field granular, no record, progressbar", async () => {
    Coucou._fields.date = fields.Date({ string: "Date" });
    serverState.debug = "1";
    const def = new Deferred();
    patchWithCleanup(CodeEditor.prototype, {
        setup() {
            super.setup();
            onMounted(() => def.resolve());
        },
    });
    const arch = `<kanban default_group_by='date:month'>
                <progressbar colors="{}" field="priority"/>
                <field name="priority" />
                <templates>
                    <t t-name='card'>
                        <field name='display_name'/>
                    </t>
                </templates>
            </kanban>`;
    onRpc("/web_studio/get_xml_editor_resources", () => ({
        main_view_key: "",
        views: [
            {
                active: true,
                arch,
                id: 99999999,
                inherit_id: false,
                name: "default view",
                xml_id: "default",
            },
        ],
    }));
    await mountViewEditor({
        type: "kanban",
        resModel: "coucou",
        arch,
    });
    expect(".o_web_studio_kanban_view_editor").toHaveClass("o_kanban_grouped");
    expect(".o_kanban_group .o_kanban_header").toHaveCount(2);
    expect(".o_kanban_grouped .o_kanban_header_title").toHaveText("Fake Group");
    expect(".o_kanban_group .o_kanban_counter").toHaveCount(2);
    expect(".o_kanban_record:not(.o_kanban_demo)").toHaveCount(1);
    await contains("button.o_web_studio_open_xml_editor").click();
    await def;
    expect(".o_web_studio_xml_editor").toHaveCount(1);
    expect(".o_view_controller.o_kanban_view").toHaveCount(1);
});

test("grouped kanban editor cannot add columns or load more", async () => {
    Coucou._records = [
        { id: 1, display_name: "Martin", priority: "2", m2o: 1 },
        { id: 2, display_name: "Jean", priority: "3", m2o: 1 },
    ];
    await mountViewEditor({
        type: "kanban",
        resModel: "coucou",
        arch: `<kanban default_group_by='m2o'>
                <templates>
                    <t t-name='card'>
                        <field name='display_name'/>
                    </t>
                </templates>
            </kanban>`,
    });
    expect(".o_kanban_load_more").toHaveCount(0);
    expect(".o_kanban_add_column").toHaveCount(0);
});

test("sortby and orderby field in kanban sidebar", async () => {
    onRpc("/web_studio/edit_view", async (request) => {
        const { params } = await request.json();
        const operation = params.operations[0];
        expect(operation.new_attrs.default_order).toBe("char_field asc");
        expect(operation.position).toBe("attributes");
        expect(operation.target.xpath_info).toEqual([{ tag: "kanban", indice: 1 }]);
        expect.step("edit_view");
        const newArch = `
            <kanban default_order="char_field asc">
                <templates>
                    <t t-name="card">
                        <h3>Card</h3>
                    </t>
                </templates>
            </kanban>
        `;
        return editView(params, "kanban", newArch);
    });
    await mountViewEditor({
        type: "kanban",
        resModel: "coucou",
        arch: `<kanban>
        <templates>
            <t t-name="card">
                <h3>Card</h3>
            </t>
        </templates>
    </kanban>
    `,
    });
    await contains(".o_web_studio_view").click();
    await contains(".o_web_studio_property_sort_by .o_select_menu .o_select_menu_toggler").click();
    await contains(".o-overlay-item:nth-child(1) .o-dropdown--menu .dropdown-item:eq(0)").click();
    expect(".o_web_studio_property_sort_by .o_select_menu .text-start").toHaveText("Char field");

    await contains(
        ".o_web_studio_property_sort_order .o_select_menu .o_select_menu_toggler"
    ).click();
    await contains(".o-overlay-item:nth-child(1) .o-dropdown--menu .dropdown-item:eq(0)").click();
    expect(".o_web_studio_property_sort_order .o_select_menu .text-start").toHaveText("Ascending");
    expect.verifySteps(["edit_view"]);
});
