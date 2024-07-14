/** @odoo-module */

import { browser } from "@web/core/browser/browser";
import {
    createViewEditor,
    makeArchChanger,
    registerViewEditorDependencies,
} from "@web_studio/../tests/client_action/view_editors/view_editor_tests_utils";
import { click, getFixture, patchWithCleanup } from "@web/../tests/helpers/utils";
import { makeFakeHTTPService } from "@web/../tests/helpers/mock_services";
import { registry } from "@web/core/registry";

/** @type {Node} */
let target;
let serverData;

QUnit.module(
    "View Editors",
    {
        async beforeEach() {
            serverData = {
                models: {
                    "res.partner": {
                        fields: {
                            name: { string: "Customer", type: "char" },
                            partner_latitude: { string: "Latitude", type: "float" },
                            partner_longitude: { string: "Longitude", type: "float" },
                            contact_address_complete: { string: "Address", type: "char" },
                            task_ids: {
                                string: "Task",
                                type: "one2many",
                                relation: "project.task",
                                relation_field: "partner_id",
                            },
                            sequence: { string: "sequence", type: "integer" },
                        },
                        records: [
                            {
                                id: 1,
                                name: "Foo",
                                partner_latitude: 10.0,
                                partner_longitude: 10.5,
                                contact_address_complete: "Chaussée de Namur 40, 1367, Ramillies",
                                sequence: 1,
                            },
                        ],
                    },
                    "project.task": {
                        fields: {
                            display_name: { string: "name", type: "char" },
                            scheduled_date: { string: "Schedule date", type: "datetime" },
                            sequence: { string: "sequence", type: "integer" },
                            partner_id: {
                                string: "partner",
                                type: "many2one",
                                relation: "res.partner",
                            },
                        },
                        records: [{ id: 1, display_name: "project", partner_id: 1 }],
                    },
                },
            };
            registerViewEditorDependencies();

            patchWithCleanup(browser, {
                setTimeout: (fn) => fn(),
            });
            registry.category("services").add("http", makeFakeHTTPService(), { force: true });

            target = getFixture();
        },
    },
    function () {
        QUnit.module("Map");

        QUnit.test("marker popup fields in editor sidebar", async function (assert) {
            serverData.models["project.task"].fields.description = { type: "char" };

            serverData.models["project.task"].records = [
                {
                    id: 1,
                    name: "first record",
                    description: "first description",
                    partner_id: 1,
                },
            ];

            serverData.models["ir.model.fields"] = {
                fields: {},
                records: [
                    {
                        id: 1,
                        name: "display_name",
                    },
                    { id: 2, name: "description" },
                ],
            };

            const changeArch = makeArchChanger();
            const arch = `<map res_partner='partner_id' routing='true' hide_name='true' hide_address='true' studio_map_field_ids="[1,2]">
                   <field name='name' string='Name'/>
                   <field name='description' string='Description'/>
                </map>`;
            await createViewEditor({
                serverData,
                type: "map",
                resModel: "project.task",
                arch,
                mockRPC: function (route, args) {
                    if (route === "/web_studio/edit_view") {
                        assert.step("edit_view");
                        assert.deepEqual(args.operations[0], {
                            type: "map_popup_fields",
                            target: { field_ids: [1], operation_type: "remove" },
                        });
                        const newArch = `
                            <map res_partner='partner_id' routing='true' hide_name='true' hide_address='true' studio_map_field_ids="[2]">
                                <field name='description' string='Description'/>
                            </map>`;
                        changeArch(args.view_id, newArch);
                    }
                },
            });

            assert.containsOnce(
                target,
                ".o_web_studio_sidebar .o_map_popup_fields",
                "Should have marker popup fields"
            );
            assert.containsN(
                target,
                ".o_web_studio_sidebar .o_map_popup_fields .badge",
                2,
                "Should have two selected fields in marker popup fields"
            );

            assert.containsOnce(
                target,
                "div.leaflet-marker-icon",
                "There should be one marker on the map"
            );

            await click(target.querySelector("div.leaflet-marker-icon"));

            assert.strictEqual(
                $(target)
                    .find(
                        ".o-map-renderer--popup-table tbody tr:first .o-map-renderer--popup-table-content-name"
                    )
                    .text()
                    .trim(),
                "Name",
                "Marker popup have should have a name field"
            );
            assert.strictEqual(
                $(target)
                    .find(
                        ".o-map-renderer--popup-table tbody tr:first .o-map-renderer--popup-table-content-value"
                    )
                    .text()
                    .trim(),
                "first record",
                "Marker popup have should have a name"
            );
            assert.strictEqual(
                $(target)
                    .find(
                        ".o-map-renderer--popup-table tbody tr:last .o-map-renderer--popup-table-content-name"
                    )
                    .text()
                    .trim(),
                "Description",
                "Marker popup have should have a Description field"
            );
            assert.strictEqual(
                $(target)
                    .find(
                        ".o-map-renderer--popup-table tbody tr:last .o-map-renderer--popup-table-content-value"
                    )
                    .text()
                    .trim(),
                "first description",
                "Marker popup have should have a description"
            );

            // Remove field and check marker popup fields
            await click(
                target.querySelector(".o_web_studio_sidebar .o_map_popup_fields .badge .o_delete")
            );
            assert.verifySteps(["edit_view"]);
            assert.containsOnce(
                target,
                ".o_web_studio_sidebar .o_map_popup_fields .badge",
                "Should have only one selected fields in marker popup fields"
            );

            await click(target.querySelector("div.leaflet-marker-icon"));
            assert.containsOnce(
                target,
                ".o-map-renderer--popup-table tbody tr",
                "Marker popup have should have only Description field"
            );
            assert.strictEqual(
                target.querySelector(
                    ".o-map-renderer--popup-table tbody tr .o-map-renderer--popup-table-content-value"
                ).textContent,
                "first description"
            );
        });

        QUnit.test("map additional fields domain", async (assert) => {
            serverData.models["ir.model.fields"] = {
                fields: {},
                records: [],
            };
            await createViewEditor({
                serverData,
                type: "map",
                resModel: "project.task",
                arch: `<map/>`,
                mockRPC(route, args) {
                    if (args.method === "name_search") {
                        assert.step("name_search");
                        assert.strictEqual(args.model, "ir.model.fields");
                        assert.deepEqual(args.kwargs.args, [
                            "&",
                            "&",
                            ["model", "=", "project.task"],
                            ["ttype", "not in", ["many2many", "one2many", "binary"]],
                            "!",
                            ["id", "in", []],
                        ]);
                    }
                },
            });
            await click(target, ".o_field_many2many_tags input");
            assert.verifySteps(["name_search"]);
        });

        QUnit.test("many2many, one2many and binary fields cannot be selected in SortBy dropdown for map editor", async function (assert) {
            assert.expect(1);

            serverData.models["project.task"].fields.display_name.store = true;

            serverData.models["project.task"].fields.o2m_field = {
                string: "One2Many Field",
                type: "one2many",
                relation: "res.partner",
                store: true,
            };

            serverData.models["project.task"].fields.m2m_field = {
                string: "Many2Many Field",
                type: "many2many",
                relation: "res.partner",
                store: true,
            };

            serverData.models["project.task"].fields.binary_field = {
                string: "Binary Field",
                type: "binary",
                store: true,
            };

            await createViewEditor({
                serverData,
                type: "map",
                resModel: "project.task",
                arch: `<map routing='true'/>`
            });

            // Check that the many2many, one2many, and binary fields cannot be selected in the SortBy dropdown
            await click(target.querySelectorAll(".dropdown-toggle.o_select_menu_toggler")[1]);
            const sortByDropdownMenu = target.querySelectorAll(".o_select_menu_item");
            assert.strictEqual(sortByDropdownMenu.length, 1, "There should be 1 items in the SortBy dropdown");
        });
    }
);
