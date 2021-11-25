/** @odoo-module **/

import { registry } from "@web/core/registry";
import { makeFakeUserService, makeFakeDialogService } from "../helpers/mock_services";
import { click, makeDeferred } from "../helpers/utils";
import {
    setupControlPanelFavoriteMenuRegistry,
    setupControlPanelServiceRegistry,
} from "../search/helpers";

import { makeView } from "../views/helpers";
import { ColorPickerDialog } from "@web/core/colorpicker/colorpicker_dialog";

const serviceRegistry = registry.category("services");

function hasGroup(group) {
    return group === "base.group_allow_export";
}

let serverData;

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(async () => {
        serverData = {
            models: {
                partner: {
                    fields: {
                        hex_color: { string: "hexadecimal color", type: "char" },
                    },
                    records: [
                        {
                            id: 1,
                            hex_color: "#ff0000",
                        },
                        {
                            id: 2,
                            hex_color: "#ff4444",
                        },
                    ],
                },
            },
        };
        setupControlPanelFavoriteMenuRegistry();
        setupControlPanelServiceRegistry();
        serviceRegistry.add("user", makeFakeUserService(hasGroup), { force: true });
    });

    QUnit.module("ColorField");

    QUnit.test("it opens a color picker dialog", async function (assert) {
        assert.expect(4);

        const dialogOpenedDeffered = makeDeferred();

        serviceRegistry.add(
            "dialog",
            makeFakeDialogService((dialogClass, props) => {
                assert.strictEqual(dialogClass, ColorPickerDialog);
                assert.strictEqual(props.color, serverData.models.partner.records[0].hex_color);
                assert.step("dialog opened");
                dialogOpenedDeffered.resolve();
            }),
            { force: true }
        );

        var form = await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 1,
            arch: `
                <form>
                    <group>
                        <field name="hex_color" widget="color" />
                    </group>
                </form>
            `,
        });

        await click(form.el.querySelector(".o_field_color button"));

        await dialogOpenedDeffered;

        assert.verifySteps(["dialog opened"]);
    });

    QUnit.test("in list, it doesn't open the form view when clicked", async function (assert) {
        assert.expect(2);

        const dialogOpenedDeffered = makeDeferred();

        serviceRegistry.add(
            "dialog",
            makeFakeDialogService(() => {
                assert.step("clicked");
                dialogOpenedDeffered.resolve();
            }),
            { force: true }
        );

        var list = await makeView({
            type: "list",
            serverData,
            resModel: "partner",
            arch: `
                <tree>
                    <field name="hex_color" widget="color" />
                </tree>
            `,
        });

        await click(list.el.querySelector(".o_field_color button"));
        await dialogOpenedDeffered;
        assert.verifySteps(["clicked"]);
    });
});
