/** @odoo-module */
import { createView } from 'web.test_utils';
import {ProjectFormView} from "@project/js/project_form";
import {patch} from "@web/core/utils/patch";
import core from "web.core";
let serverData = null;

const ProjectFormController = ProjectFormView.prototype.config.Controller;
QUnit.module("Project", hooks => {
    hooks.beforeEach(() => {
        serverData = {
            project: {
                fields: {
                    id: { string: "Id", type: "integer" },
                },
                records: [
                    { id: 1, display_name: "First record"},
                ],
            },
        }
    })
    QUnit.module("Form");
    QUnit.test("project form view", async function (assert) {
        /*
        This is a test whitebox because the flow cannot be reproduced correctly otherwise.
        The idea is to check that the DOM_updated event is not triggered twice to avoid a crash.
        */
        patch(ProjectFormController.prototype, "patchedInit", {
            init: function () {
                this._super(...arguments);
                core.bus.trigger("DOM_updated");
            }
        });
        const form = await createView({
            View: ProjectFormView,
            model: 'project',
            data: serverData,
            arch: '<form><field name="display_name"/></form>',
        });
        assert.containsOnce(document.body, form.el);
        form.destroy()
    })
});
