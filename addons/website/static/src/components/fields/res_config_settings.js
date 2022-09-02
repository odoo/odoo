/** @odoo-module **/

import { BooleanField } from '@web/views/fields/boolean/boolean_field';
import { Dialog } from '@web/core/dialog/dialog';
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const { Component } = owl;

class CookieBarDialog extends Component {
    accept() {
        this.props.accept();
        this.props.close();
    }
}
CookieBarDialog.components = { Dialog };
CookieBarDialog.template = 'website.res_config_settings.CookieDialog';

class WebsiteCookiebarField extends BooleanField {
    setup() {
        this.dialog = useService('dialog');
    }

    onChange(newValue) {
        if (!newValue) {
            return this.props.update(newValue);
        }
        let value = false;
        this.dialog.add(CookieBarDialog, {
            title: "Website Cookie Bar",
            accept: () => {
                value = true;
            },
        }, {
            onClose: () => {
                this.props.update(value);
            }
        });
    }
}
registry.category("fields").add("website_cookiesbar_field", WebsiteCookiebarField);
