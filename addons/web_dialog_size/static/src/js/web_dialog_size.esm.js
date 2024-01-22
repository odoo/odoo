/** @odoo-module **/

import {ActionDialog} from "@web/webclient/actions/action_dialog";
import {patch} from "@web/core/utils/patch";
import rpc from "web.rpc";
import {Component, onMounted} from "@odoo/owl";
import {Dialog} from "@web/core/dialog/dialog";
import {SelectCreateDialog} from "@web/views/view_dialogs/select_create_dialog";

export class ExpandButton extends Component {
    setup() {
        this.last_size = this.props.getsize();
        this.config = rpc.query({
            model: "ir.config_parameter",
            method: "get_web_dialog_size_config",
        });

        onMounted(() => {
            var self = this;
            this.config.then(function (r) {
                if (r.default_maximize && stop) {
                    self.dialog_button_extend();
                }
            });
        });
    }

    dialog_button_extend() {
        this.props.setsize("dialog_full_screen");
        this.render();
    }

    dialog_button_restore() {
        this.props.setsize(this.last_size);
        this.render();
    }
}

ExpandButton.template = "web_dialog_size.ExpandButton";

patch(Dialog.prototype, "web_dialog_size.Dialog", {
    setup() {
        this._super(...arguments);
        this.setSize = this.setSize.bind(this);
        this.getSize = this.getSize.bind(this);
    },

    setSize(size) {
        this.props.size = size;
        this.render();
    },

    getSize() {
        return this.props.size;
    },
});

patch(SelectCreateDialog.prototype, "web_dialog_size.SelectCreateDialog", {
    setup() {
        this._super(...arguments);
        this.setSize = this.setSize.bind(this);
        this.getSize = this.getSize.bind(this);
    },

    setSize(size) {
        this.props.size = size;
        this.render();
    },

    getSize() {
        return this.props.size;
    },
});

Object.assign(ActionDialog.components, {ExpandButton});
SelectCreateDialog.components = Object.assign(SelectCreateDialog.components || {}, {
    ExpandButton,
});
Dialog.components = Object.assign(Dialog.components || {}, {ExpandButton});
// Patch annoying validation method
Dialog.props.size.validate = (s) =>
    ["sm", "md", "lg", "xl", "dialog_full_screen"].includes(s);
