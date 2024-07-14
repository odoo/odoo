/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, {
    performRPC(route, args) {
        if (route === "/web/dataset/call_kw/res.users/has_group") {
            return true;
        }
        if (route === "/web_studio/activity_allowed") {
            return Promise.resolve(this.mockActivityAllowed());
        }
        if (route === "/web_studio/get_studio_view_arch") {
            return Promise.resolve(this.mockGetStudioViewArch());
        }
        if (route === "/web_studio/chatter_allowed") {
            return Promise.resolve(this.mockChatterAllowed());
        }
        if (route === "/web_studio/get_default_value") {
            return Promise.resolve(this.mockGetDefaultValue());
        }
        if (route === "/web_studio/get_studio_action") {
            return Promise.resolve(this.mockGetStudioAction(args));
        }
        if (route === "/web_studio/edit_view") {
            return Promise.resolve(this.mockEditView(args));
        }
        if (route === "/web_studio/edit_view_arch") {
            return Promise.resolve(this.mockEditView(args));
        }
        if (route === "/web_studio/get_studio_view_arch") {
            return Promise.resolve(this.mockGetStudioViewArch(args));
        }

        return super.performRPC(...arguments);
    },

    mockActivityAllowed() {
        return false;
    },

    mockChatterAllowed() {
        return false;
    },

    mockGetStudioViewArch() {
        return {
            studio_view_id: "__test_studio_view_arch__",
            studio_view_arch: "<data/>",
        };
    },

    mockGetDefaultValue() {
        return {};
    },

    mockGetStudioAction(args) {
        if (args.action_name === "reports") {
            return {
                name: "Reports",
                res_model: "ir.actions.report",
                target: "current",
                type: "ir.actions.act_window",
                views: [[false, "kanban"]],
            };
        } else if (args.action_name === "automations") {
            return {
                name: "Automation Rules",
                type: "ir.actions.act_window",
                res_model: "base.automation",
                views: [
                    [false, "kanban"],
                    [false, "list"],
                    [false, "form"],
                ],
                target: "current",
                domain: [],
                help: /*xml*/ `
                    <p class="no_content_helper_class">
                        This text content is needed here, otherwise the paragraph won't be rendered.
                    </p>
                `,
            };
        }
    },

    _getViewFromId(viewId) {
        const uniqueViewKey = Object.keys(this.archs)
            .map((k) => k.split(","))
            .filter(([model, vid, vtype]) => vid === `${viewId}`);

        if (!uniqueViewKey.length) {
            throw new Error(`No view with id "${viewId}" in edit_view`);
        }
        if (uniqueViewKey.length > 1) {
            throw new Error(
                `There are multiple views with id "${viewId}", and probably for different models.`
            );
        }
        const [modelName, , viewType] = uniqueViewKey[0];
        return {
            resModel: modelName,
            viewType,
            key: uniqueViewKey[0],
        };
    },

    mockEditView(args) {
        const viewId = args.view_id;
        if (!viewId) {
            throw new Error(
                "To use the 'edit_view' mocked controller, you should specify a unique id on the view you are editing"
            );
        }
        const { resModel, viewType } = this._getViewFromId(viewId);
        const view = this.getView(resModel, [viewId, viewType], {
            context: args.context,
            options: {},
        });
        const models = {};
        for (const resModel of Object.keys(view.models)) {
            models[resModel] = this.mockFieldsGet(resModel);
        }
        return {
            views: {
                [viewType]: view,
            },
            models,
            studio_view_id: false,
        };
    },
});
