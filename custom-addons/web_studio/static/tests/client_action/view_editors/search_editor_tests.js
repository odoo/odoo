/** @odoo-module */
import {
    getFixture,
    dragAndDrop,
    drag,
    click,
    nextTick,
    patchWithCleanup,
} from "@web/../tests/helpers/utils";
import {
    createViewEditor,
    disableHookAnimation,
    registerViewEditorDependencies,
} from "@web_studio/../tests/client_action/view_editors/view_editor_tests_utils";
import { MockServer } from "@web/../tests/helpers/mock_server";
import { pick } from "@web/core/utils/objects";

function makeArchChanger() {
    let mockServer = null;
    patchWithCleanup(MockServer.prototype, {
        init() {
            super.init(...arguments);
            mockServer = this;
        },
    });

    return (viewId, arch) => {
        const viewDescr = mockServer._getViewFromId(viewId);
        mockServer.archs[viewDescr.key] = arch;
    };
}

QUnit.module("View Editors", (hooks) => {
    QUnit.module("Search Editor");

    let target;
    let serverData;
    let changeArch;

    hooks.beforeEach(() => {
        target = getFixture();
        serverData = {
            models: {
                coucou: {},
            },
        };

        registerViewEditorDependencies();
        changeArch = makeArchChanger();
    });

    QUnit.test("empty search editor", async function (assert) {
        await createViewEditor({
            serverData,
            resModel: "coucou",
            arch: "<search/>",
            type: "search",
        });

        assert.containsOnce(
            target,
            ".o_web_studio_search_view_editor",
            "there should be a search editor"
        );
        assert.containsOnce(
            target,
            ".o-web-studio-search--fields .o_web_studio_hook",
            "there should be one hook in the autocompletion fields"
        );
        assert.containsOnce(
            target,
            ".o-web-studio-search--filters .o_web_studio_hook",
            "there should be one hook in the filters"
        );
        assert.containsOnce(
            target,
            ".o-web-studio-search--groupbys .o_web_studio_hook",
            "there should be one hook in the group by"
        );
        assert.containsNone(
            target,
            ".o_web_studio_search_view_editor [data-studio-xpath]",
            "there should be no node"
        );
    });

    QUnit.test("search editor", async function (assert) {
        const arch = `
            <search>
                <field name='display_name'/>
                <filter string='My Name'
                    name='my_name'
                    domain='[("display_name","=",coucou)]'
                />
                <group expand='0' string='Filters'>
                    <filter string='My Name2'
                        name='my_name2'
                        domain='[("display_name","=",coucou2)]'
                />
                </group>
                <group expand='0' string='Group By'>
                    <filter name='groupby_display_name'
                    domain='[]' context="{'group_by':'display_name'}"/>
                </group>
            </search>`;

        await createViewEditor({
            serverData,
            type: "search",
            resModel: "coucou",
            arch: arch,
            mockRPC: function (route, args) {
                if (route === "/web_studio/edit_view") {
                    assert.step("edit_view");
                    assert.deepEqual(
                        args.operations[0].node.attrs,
                        { name: "display_name" },
                        "we should only specify the name (in attrs) when adding a field"
                    );
                }
            },
        });

        // try to add a field in the autocompletion section
        assert.containsOnce(
            target,
            ".o_web_studio_search_view_editor",
            "there should be a search editor"
        );
        assert.containsN(
            target,
            ".o-web-studio-search--fields .o_web_studio_hook",
            2,
            "there should be two hooks in the autocompletion fields"
        );
        assert.containsN(
            target,
            ".o-web-studio-search--filters .o_web_studio_hook",
            4,
            "there should be four hook in the filters"
        );
        assert.containsN(
            target,
            ".o-web-studio-search--groupbys .o_web_studio_hook",
            2,
            "there should be two hooks in the group by"
        );
        assert.containsOnce(
            target,
            ".o-web-studio-search--fields [data-studio-xpath]",
            "there should be 1 node in the autocompletion fields"
        );
        assert.containsN(
            target,
            ".o-web-studio-search--filters [data-studio-xpath]",
            2,
            "there should be 2 nodes in the filters"
        );
        assert.containsOnce(
            target,
            ".o-web-studio-search--groupbys [data-studio-xpath]",
            "there should be 1 nodes in the group by"
        );
        assert.containsN(
            target,
            ".o_web_studio_search_view_editor [data-studio-xpath]",
            4,
            "there should be 4 nodes"
        );

        // edit the autocompletion field
        await click(
            target.querySelector(
                ".o_web_studio_search_view_editor .o_web_studio_search_autocompletion_container [data-studio-xpath]"
            )
        );

        assert.strictEqual(
            target.querySelector(".o_web_studio_sidebar.o_notebook .nav-link.active").textContent,
            "Properties"
        );
        assert.strictEqual(
            target.querySelector(".o_web_studio_sidebar .o_web_studio_property input[name='label']")
                .value,
            "Display Name"
        );

        assert.hasClass(
            target.querySelector(
                ".o_web_studio_search_view_editor .o_web_studio_search_autocompletion_container [data-studio-xpath]"
            ),
            "o-web-studio-editor--element-clicked",
            "the field should have the clicked style"
        );

        await click(target.querySelector(".o_web_studio_sidebar .nav-link:nth-child(1)"));
        assert.containsN(target, ".o_web_studio_existing_fields > .o-draggable", 4, "four fields should be available draggable in the view");

        await dragAndDrop(
            target.querySelector(
                `.o_web_studio_existing_fields > .o-draggable.o_web_studio_field_char`
            ),
            target.querySelector(".o-web-studio-search--fields .o_web_studio_hook:nth-child(1)")
        );
        await nextTick();
        assert.verifySteps(["edit_view"]);
        assert.containsN(target, ".o_web_studio_existing_fields > .o-draggable", 4, "four fields are still available to drag");
    });

    QUnit.test("delete a field", async function (assert) {
        const arch = `<search>
                <field name='display_name'/>
            </search>`;
        await createViewEditor({
            serverData,
            resModel: "coucou",
            type: "search",
            arch: arch,
            mockRPC: function (route, args) {
                if (route === "/web_studio/edit_view") {
                    assert.step("edit_view");
                    assert.deepEqual(args.operations[0], {
                        target: {
                            attrs: { name: "display_name" },
                            tag: "field",
                            xpath_info: [
                                {
                                    indice: 1,
                                    tag: "search",
                                },
                                {
                                    indice: 1,
                                    tag: "field",
                                },
                            ],
                        },
                        type: "remove",
                    });
                    changeArch(args.view_id, "<search />");
                }
            },
        });

        assert.containsOnce(target, "[data-studio-xpath]", "there should be one node");
        // edit the autocompletion field
        await click(
            target.querySelector(
                ".o_web_studio_search_autocompletion_container [data-studio-xpath]"
            )
        );
        await click(target.querySelector(".o_web_studio_sidebar .o_web_studio_remove"));
        await click(target.querySelector(".modal footer .btn-primary"));
        assert.verifySteps(["edit_view"]);

        assert.containsNone(target, "[data-studio-xpath]", "there should be no node anymore");
    });

    QUnit.test(
        'indicate that regular stored field(except date/datetime) can not be dropped in "Filters" section',
        async function (assert) {
            serverData.models.coucou.fields = {
                name: { type: "char", store: true },
            };
            await createViewEditor({
                serverData,
                resModel: "coucou",
                type: "search",
                arch: `<search>
                <field name='display_name'/>
                <filter string='My Name'
                    name='my_name'
                    domain='[("display_name","=",coucou)]'
                />
                <group expand='0' string='Filters'>
                    <filter string='My Name2'
                        name='my_name2'
                        domain='[("display_name","=",coucou2)]'
                />
                </group>
                <group expand='0' string='Group By'>
                    <filter name='groupby_display_name'
                    domain='[]' context="{'group_by':'display_name'}"/>
                </group>
            </search>`,
            });

            // try to add a stored char field in the filters section
            const { cancel, moveTo } = await drag(
                target.querySelectorAll(
                    ".o_web_studio_existing_fields .o-draggable.o_web_studio_field_char"
                )[1]
            );
            await moveTo(".o_web_studio_hook");
            assert.hasClass(
                target.querySelector(".o-web-studio-search--filters"),
                "o-web-studio-search--drop-disable",
                "filter section should be muted"
            );
            assert.doesNotHaveClass(
                target.querySelector(".o-web-studio-search--groupbys"),
                "o-web-studio-search--drop-disable",
                "groupby section should not be muted"
            );
            assert.doesNotHaveClass(
                target.querySelector(".o-web-studio-search--fields"),
                "o-web-studio-search--drop-disable",
                "autocompletion_fields section should not be muted"
            );
            await cancel();
        }
    );

    QUnit.test(
        'indicate that ungroupable field can not be dropped in "Filters" and "Group by" sections',
        async function (assert) {
            assert.expect(3);

            await createViewEditor({
                serverData,
                type: "search",
                resModel: "coucou",
                arch: `<search>
                <field name='display_name'/>
                <filter string='My Name'
                    name='my_name'
                    domain='[("display_name","=",coucou)]'
                />
                <group expand='0' string='Filters'>
                    <filter string='My Name2'
                        name='my_name2'
                        domain='[("display_name","=",coucou2)]'
                    />
                </group>
                <group expand='0' string='Group By'>
                    <filter name='groupby_display_name'
                    domain='[]' context="{'group_by':'display_name'}"/>
                </group>
            </search>`,
            });

            const { cancel, moveTo } = await drag(
                target.querySelector(
                    ".o_web_studio_existing_fields .o-draggable.o_web_studio_field_integer"
                )
            );
            await moveTo(".o_web_studio_hook");

            // try to add integer field in groupby
            assert.hasClass(
                target.querySelector(".o-web-studio-search--groupbys"),
                "o-web-studio-search--drop-disable",
                "groupby section should be muted"
            );
            assert.hasClass(
                target.querySelector(".o-web-studio-search--filters"),
                "o-web-studio-search--drop-disable",
                "filter section should be muted"
            );
            assert.doesNotHaveClass(
                target.querySelector(".o-web-studio-search--fields"),
                "o-web-studio-search--drop-disable",
                "autocompletion_fields section should be muted"
            );
            await cancel();
        }
    );

    QUnit.test('many2many field can be dropped in "Group by" sections', async function (assert) {
        const arch = `<search>
                <field name='display_name'/>
                <filter string='My Name' name='my_name' domain='[("display_name","=",coucou)]' />
                <group expand='0' string='Filters'>
                    <filter string='My Name2' name='my_name2' domain='[("display_name","=",coucou2)]'/>
                </group>
                <group expand='0' string='Group By'>
                    <filter name='groupby_display_name' domain='[]' context="{'group_by':'display_name'}"/>
                    <filter name='groupby_m2m' domain='[]' context="{'group_by':'m2m'}"/>
                </group>
            </search>`;
        serverData.models.coucou = {
            fields: {
                m2m: { type: "many2many", string: "M2M", store: true },
            },
        };

        await createViewEditor({
            serverData,
            type: "search",
            resModel: "coucou",
            arch: `<search>
                    <field name='display_name'/>
                    <filter string='My Name' name='my_name' domain='[("display_name","=",coucou)]' />
                    <group expand='0' string='Filters'>
                        <filter string='My Name2' name='my_name2' domain='[("display_name","=",coucou2)]'/>
                    </group>
                    <group expand='0' string='Group By'>
                        <filter name='groupby_display_name' domain='[]' context="{'group_by':'display_name'}"/>
                    </group>
                </search>`,
            mockRPC: function (route, args) {
                if (route === "/web_studio/edit_view") {
                    assert.step("edit_view");
                    assert.strictEqual(
                        args.operations[0].node.attrs.context,
                        "{'group_by': 'm2m'}"
                    );
                    changeArch(args.view_id, arch);
                }
            },
        });

        assert.containsN(
            target,
            ".o-web-studio-search--groupbys [data-studio-xpath]",
            1,
            "should have 1 group inside groupby dropdown"
        );

        // try to add many2many field in groupby
        await dragAndDrop(
            target.querySelector(".o_web_studio_existing_fields > .o_web_studio_field_many2many"),
            target.querySelector(".o-web-studio-search--groupbys .o_web_studio_hook")
        );
        assert.verifySteps(["edit_view"]);
        assert.containsN(
            target,
            ".o-web-studio-search--groupbys [data-studio-xpath]",
            2,
            "should have 2 group inside groupby dropdown"
        );
    });

    QUnit.test(
        "existing field section should be unfolded by default in search",
        async function (assert) {
            assert.expect(2);

            await createViewEditor({
                serverData,
                type: "search",
                resModel: "coucou",
                arch: `<search>
            <field name='display_name'/>
        </search>`,
            });

            assert.hasClass(
                target.querySelector(".o_web_studio_existing_fields_header i"),
                "fa-caret-down",
                "should have a existing fields unfolded"
            );
            assert.isVisible(
                target.querySelector(".o_web_studio_existing_fields_section"),
                "the existing fields section should be visible"
            );
        }
    );

    QUnit.test(
        'indicate that separators can not be dropped in "Automcompletion Fields" and "Group by" sections',
        async function (assert) {
            await createViewEditor({
                serverData,
                type: "search",
                resModel: "coucou",
                arch: `<search>
                <field name='display_name'/>
                <filter string='My Name'
                    name='my_name'
                    domain='[("display_name","=",coucou)]'
                />
                <group expand='0' string='Filters'>
                <filter string='My Name2'
                    name='my_name2'
                    domain='[("display_name","=",coucou2)]'
                />
                </group>
                <group expand='0' string='Group By'>
                <filter name='groupby_display_name'
                    domain='[]' context="{'group_by':'display_name'}"/>
                </group>
            </search>`,
            });

            // try to add seperator in groupby
            const { cancel, moveTo } = await drag(
                target.querySelector(".o-draggable.o_web_studio_filter_separator")
            );
            await moveTo(".o_web_studio_hook");
            assert.hasClass(
                target.querySelector(".o-web-studio-search--groupbys"),
                "o-web-studio-search--drop-disable",
                "groupby section should be muted"
            );
            assert.hasClass(
                target.querySelector(".o-web-studio-search--fields"),
                "o-web-studio-search--drop-disable",
                "autocompletion_fields section should be muted"
            );
            assert.doesNotHaveClass(
                target.querySelector(".o-web-studio-search--filters"),
                "o-web-studio-search--drop-disable",
                "filter section should not be muted"
            );
            await cancel();
        }
    );

    QUnit.test(
        'indicate that filter can not be dropped in "Automcompletion Fields" and "Group by" sections',
        async function (assert) {
            await createViewEditor({
                serverData,
                type: "search",
                resModel: "coucou",
                arch: `<search>
                <field name='display_name'/>
                <filter string='My Name'
                    name='my_name'
                    domain='[("display_name","=",coucou)]'
                />
                <group expand='0' string='Filters'>
                <filter string='My Name2'
                    name='my_name2'
                    domain='[("display_name","=",coucou2)]'
                />
                </group>
                <group expand='0' string='Group By'>
                <filter name='groupby_display_name'
                    domain='[]' context="{'group_by':'display_name'}"/>
                </group>
            </search>`,
            });

            const { cancel, moveTo } = await drag(
                target.querySelector(".o-draggable.o_web_studio_filter")
            );
            await moveTo(".o_web_studio_hook");
            assert.hasClass(
                target.querySelector(".o-web-studio-search--groupbys"),
                "o-web-studio-search--drop-disable",
                "groupby section should be muted"
            );
            assert.hasClass(
                target.querySelector(".o-web-studio-search--fields"),
                "o-web-studio-search--drop-disable",
                "autocompletion_fields section should be muted"
            );
            assert.doesNotHaveClass(
                target.querySelector(".o-web-studio-search--filters"),
                "o-web-studio-search--drop-disable",
                "filter section should not be muted"
            );
            await cancel();
        }
    );

    QUnit.test("move a date/datetime field in search filter dropdown", async function (assert) {
        const arch = `<search>
            <field name='display_name'/>
            <filter string='Start Date'
                name='start'
                date='start'
            />
            <filter string='My Name'
                name='my_name'
                domain='[("display_name","=",coucou)]'
            />
            <filter string='My Name2'
                name='my_name2'
                domain='[("display_name","=",coucou2)]'
            />
            </search>`;

        serverData.models.coucou.fields = {
            priority: {
                string: "Priority",
                type: "selection",
                manual: true,
                selection: [
                    ["1", "Low"],
                    ["2", "Medium"],
                    ["3", "High"],
                ],
                store: true,
            },
            start: { string: "Start Date", type: "datetime", store: true },
        };

        await createViewEditor({
            serverData,
            type: "search",
            resModel: "coucou",
            arch: `<search>
                <field name='display_name'/>
                <filter string='My Name'
                    name='my_name'
                    domain='[("display_name","=",coucou)]'
                />
                <filter string='My Name2'
                    name='my_name2'
                    domain='[("display_name","=",coucou2)]'
                />
                </search>`,
            mockRPC: function (route, args) {
                if (route === "/web_studio/edit_view") {
                    assert.step("edit_view");
                    assert.strictEqual(args.operations[0].node.tag, "filter");
                    assert.strictEqual(
                        args.operations[0].node.attrs.date,
                        "start",
                        "should date attribute in attrs when adding a date/datetime field"
                    );
                    changeArch(args.view_id, arch);
                }
            },
        });

        assert.containsN(
            target,
            ".o_web_studio_search_sub_item.o-web-studio-search--filters .o_web_studio_hook",
            3,
            "there should be three hooks in the filters dropdown"
        );
        // try to add a field other date/datetime in the filters section
        await dragAndDrop(
            target.querySelector(".o_web_studio_existing_fields .o_web_studio_field_selection"),
            target.querySelector(
                ".o_web_studio_search_sub_item.o-web-studio-search--filters .o_web_studio_hook"
            )
        );
        assert.containsN(
            target,
            ".o_web_studio_search_sub_item.o-web-studio-search--filters [data-studio-xpath]",
            2,
            "should have two filters inside filters dropdown"
        );

        // try to add a date field in the filters section
        const startField = Array.from(
            target.querySelectorAll(
                ".o_web_studio_existing_fields .o-draggable.o_web_studio_field_datetime"
            )
        ).filter((el) => el.textContent === "Start Date")[0];
        await dragAndDrop(
            startField,
            target.querySelector(
                ".o_web_studio_search_sub_item.o-web-studio-search--filters .o_web_studio_hook"
            )
        );
        assert.verifySteps(["edit_view"]);
        assert.containsN(
            target,
            ".o_web_studio_search_sub_item.o-web-studio-search--filters .o_web_studio_hook",
            4,
            "there should be four hooks in the filters dropdown"
        );
        assert.containsN(
            target,
            ".o_web_studio_search_sub_item.o-web-studio-search--filters [data-studio-xpath]",
            3,
            "should have three filters inside filters dropdown"
        );
    });

    QUnit.test("empty search editor: drag a groupby", async function (assert) {
        serverData.models.coucou.fields = {
            __last_update: {
                type: "datetime",
                store: true,
                string: "Last Updated on",
            },
        };

        await createViewEditor({
            serverData,
            type: "search",
            resModel: "coucou",
            arch: `<search/>`,
            mockRPC: function (route, args) {
                if (route === "/web_studio/edit_view") {
                    assert.step("edit_view");
                    assert.deepEqual(
                        pick(args.operations[0].node.attrs, "context", "create_group", "string"),
                        {
                            string: "Last Updated on",
                            context: "{'group_by': '__last_update'}",
                            create_group: true,
                        }
                    );

                    changeArch(
                        args.view_id,
                        `
                        <search>
                            <group name="studio_group_by">
                                <filter name="studio_group_by_abcdef" string="Last Updated on" context="{'group_by': 'write_date'}" />
                            </group>
                        </search>`
                    );
                }
            },
        });
        disableHookAnimation(target);

        await dragAndDrop(
            target.querySelector(
                `.o_web_studio_sidebar .o_web_studio_existing_fields > .o-draggable[data-drop='${JSON.stringify(
                    { fieldName: "__last_update" }
                )}']`
            ),
            target.querySelector(
                ".o_web_studio_view_renderer .o-web-studio-search--groupbys .o_web_studio_hook"
            )
        );
        assert.verifySteps(["edit_view"]);

        assert.containsOnce(
            target,
            ".o-web-studio-search--groupbys .o-web-studio-editor--element-clickable"
        );
        assert.strictEqual(
            target
                .querySelector(
                    ".o-web-studio-search--groupbys .o-web-studio-editor--element-clickable"
                )
                .textContent.trim(),
            "Last Updated on"
        );
    });
});
