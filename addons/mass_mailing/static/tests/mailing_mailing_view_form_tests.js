/** @odoo-module **/

import { setupViewRegistries } from "@web/../tests/views/helpers";
import { patchWithCleanup } from "@web/../tests/helpers/utils";
import { createWebClient, doAction } from "@web/../tests/webclient/helpers";
import { MassMailingFullWidthViewController } from "@mass_mailing/js/mailing_mailing_view_form_full_width";

let serverData;

QUnit.module("mass_mailing", {}, function () {
    QUnit.module("MassMailingFullWidthViewController", (hooks) => {
        hooks.beforeEach(() => {
            serverData = {
                models: {
                    partner: {
                        fields: {
                            display_name: { string: "Displayed name", type: "char" },
                        },
                    },
                },

                actions: {
                    1: {
                        id: 1,
                        name: "test",
                        res_model: "partner",
                        type: "ir.actions.act_window",
                        views: [[false, "form"]],
                    },
                    2: {
                        id: 2,
                        name: "test",
                        res_model: "partner",
                        type: "ir.actions.act_window",
                        views: [[false, "list"]],
                    },
                },

                views: {
                    "partner,false,form": `<form js_class="mailing_mailing_view_form_full_width">
                        <field name="display_name"/>
                    </form>`,
                    "partner,false,list": `<tree><field name="display_name"/></tree>`,
                    "partner,false,search": `<search/>`,
                },
            };

            setupViewRegistries();
        });

        QUnit.test("unregister ResizeObserver on unmount", async (assert) => {
            patchWithCleanup(MassMailingFullWidthViewController.prototype, {
                setup() {
                    super.setup();
                    patchWithCleanup(this._resizeObserver, {
                        disconnect() {
                            assert.step("disconnect");
                            return super.disconnect(...arguments);
                        },
                    });
                },
            });

            const webClient = await createWebClient({ serverData });
            await doAction(webClient, 1);
            assert.verifySteps([]);
            await doAction(webClient, 2);
            assert.verifySteps(["disconnect"]);
        });
    });
});
