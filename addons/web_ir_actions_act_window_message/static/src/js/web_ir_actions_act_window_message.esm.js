/** @odoo-module **/

import Dialog from "web.Dialog";
import {registry} from "@web/core/registry";

function _refreshWidget(env) {
    const controller = env.services.action.currentController;
    const props = controller.props;
    const view = controller.view;
    // LEGACY CODE COMPATIBILITY: remove when controllers will be written in owl
    if (view.isLegacy) {
        // Case where a legacy view is reloaded via the view switcher
        const {__legacy_widget__} = controller.getLocalState();
        const params = {};
        if ("resId" in props) {
            params.currentId = props.resId;
        }
        return __legacy_widget__.reload(params);
    }
    // END LEGACY CODE COMPATIBILITY
    env.services.action.switchView(props.type, {resId: props.resId});
}

function ir_actions_act_window_message_get_buttons(env, action, close_func) {
    // Return an array of button definitions from action
    return _.map(action.buttons || [], function (button_definition) {
        return {
            text: button_definition.name || "No name set",
            classes: button_definition.classes || "btn-default",
            click: function () {
                if (button_definition.type === "method") {
                    env.services
                        .rpc("/web/dataset/call_button", {
                            model: button_definition.model,
                            method: button_definition.method,
                            args: button_definition.args,
                            kwargs: button_definition.kwargs,
                        })
                        .then(function (result) {
                            if (_.isObject(result)) {
                                return env.services.action.doAction(result);
                            }
                            _refreshWidget(env);
                        });
                } else {
                    return env.services.action.doAction(button_definition);
                }
                close_func();
            },
        };
    });
}

async function _executeWindowMessageAction({env, action}) {
    var buttons = [];
    if (action.close_button_title !== false) {
        buttons.push({
            text: action.close_button_title || env._t("Close"),
            click: function () {
                // Refresh the view before closing the dialog
                _refreshWidget(env);
                this.close();
            },
            classes: "btn-default",
        });
    }

    var is_html = action.is_html_message === true;
    var content_properties = {};

    if (is_html) {
        content_properties = {
            html: action.message,
        };
    } else {
        content_properties = {
            text: action.message,
            css: {
                "white-space": "pre-line",
            },
        };
    }
    var dialog = new Dialog(
        this,
        _.extend({
            size: "medium",
            title: action.title,
            $content: $("<div>", content_properties),
            buttons: buttons.concat(
                ir_actions_act_window_message_get_buttons(env, action, function () {
                    dialog.close();
                })
            ),
        })
    );
    return dialog.open()._opened;
}

registry
    .category("action_handlers")
    .add("ir.actions.act_window.message", _executeWindowMessageAction);
