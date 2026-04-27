/** @odoo-module **/

import { click, getFixture, mount, editSelect } from "@web/../tests/helpers/utils";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import {
    makeFakeDialogService,
    makeFakeLocalizationService,
} from "@web/../tests/helpers/mock_services";
import { InitialsAllPagesDialog } from "@sign/dialogs/dialogs";
import { registry } from "@web/core/registry";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { uiService } from "@web/core/ui/ui_service";

const serviceRegistry = registry.category("services");

let target;
const roles = { 1: { name: "test" }, 2: { name: "selection 1" } };
const responsible = 1;
let pageCount = 3;

QUnit.module("initial all pages dialog", function (hooks) {
    const mountInitialAllPagesDialog = async (additionalProps = {}) => {
        const env = await makeTestEnv();
        env.dialogData = {
            isActive: true,
            close: () => {},
        };

        await mount(InitialsAllPagesDialog, target, {
            props: {
                addInitial: () => {},
                close: () => {},
                roles,
                responsible,
                pageCount,
                ...additionalProps,
            },
            env,
        });
    };

    hooks.beforeEach(() => {
        target = getFixture();
        serviceRegistry.add("dialog", makeFakeDialogService());
        serviceRegistry.add("localization", makeFakeLocalizationService());
        serviceRegistry.add("ui", uiService);
        serviceRegistry.add("hotkey", hotkeyService);
    });

    QUnit.test("initial all pages dialog is rendered correctly", async (assert) => {
        await mountInitialAllPagesDialog();

        const selectEl = target.querySelector("#responsible_select_initials_input");

        assert.containsOnce(target, "#responsible_select_initials_input", "should render select");
        assert.containsN(target, "option", Object.keys(roles).length);
        assert.strictEqual(
            selectEl.querySelector("option:checked").textContent,
            roles[responsible].name,
            "test role should be selected by default"
        );
    });

    QUnit.test(
        "initial all pages dialog is rendered with correct role in the selection",
        async (assert) => {
            const currentRole = 2;
            await mountInitialAllPagesDialog({
                responsible: currentRole,
            });

            const selectEl = target.querySelector("#responsible_select_initials_input");

            assert.strictEqual(
                selectEl.querySelector("option:checked").textContent,
                roles[currentRole].name,
                "test role should be selected by default"
            );
        }
    );

    QUnit.test(
        "initial all pages dialog calls addInitial with the correct role",
        async (assert) => {
            await mountInitialAllPagesDialog({
                addInitial(role, all) {
                    if (role === newResponsible) {
                        if (all) {
                            return assert.step("add-multiple-initials");
                        }
                        return assert.step("add-initial");
                    }
                },
            });

            const selectEl = target.querySelector("#responsible_select_initials_input");
            const newResponsible = 2;

            await editSelect(selectEl, "", newResponsible);
            assert.strictEqual(
                selectEl.querySelector("option:checked").textContent,
                roles[newResponsible].name,
                "role should be changed to selection 1"
            );

            await click(target, ".btn-primary");
            await click(target, ".btn-secondary");

            assert.verifySteps(["add-initial", "add-multiple-initials"]);
        }
    );
});
