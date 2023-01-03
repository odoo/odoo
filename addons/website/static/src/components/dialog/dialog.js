/** @odoo-module **/

import { useAutofocus, useService } from '@web/core/utils/hooks';
import { Dialog } from '@web/core/dialog/dialog';
import { Switch } from '@website/components/switch/switch';
import {unslugHtmlDataObject} from '../../services/website_service';
import {csrf_token, _t} from 'web.core';

const { xml, useState, Component, onWillStart } = owl;

const NO_OP = () => {};

export class WebsiteDialog extends Component {
    setup() {
        this.state = useState({
            disabled: false,
        });
    }
    /**
     * Disables the buttons of the dialog when a click is made.
     * If a handler is provided, await for its call.
     * If the prop closeOnClick is true, close the dialog.
     * Otherwise, restore the button.
     *
     * @param handler {function|void} The handler to protect.
     * @returns {function(): Promise} handler called when a click is made.
     */
    protectedClick(handler) {
        return async () => {
            if (this.state.disabled) {
                return;
            }
            this.state.disabled = true;
            if (handler) {
                await handler();
            }
            if (this.props.closeOnClick) {
                return this.props.close();
            }
            this.state.disabled = false;
        }
    }

    get contentClasses() {
        const websiteDialogClass = 'o_website_dialog';
        if (this.props.contentClass) {
            return `${websiteDialogClass} ${this.props.contentClass}`;
        }
        return websiteDialogClass;
    }
}
WebsiteDialog.components = { Dialog };
WebsiteDialog.props = {
    ...Dialog.props,
    primaryTitle: { type: String, optional: true },
    primaryClick: { type: Function, optional: true },
    secondaryTitle: { type: String, optional: true },
    secondaryClick: { type: Function, optional: true },
    showSecondaryButton: { type: Boolean, optional: true },
    close: { type: Function, optional: true },
    closeOnClick: { type: Boolean, optional: true },
    body: { type: String, optional: true },
    slots: { type: Object, optional: true },
};
WebsiteDialog.defaultProps = {
    ...Dialog.defaultProps,
    title: _t("Confirmation"),
    primaryTitle: _t("Ok"),
    secondaryTitle: _t("Cancel"),
    showSecondaryButton: true,
    size: "md",
    closeOnClick: true,
    close: NO_OP,
};
WebsiteDialog.template = "website.WebsiteDialog";

export class AddPageDialog extends Component {
    setup() {
        super.setup();
        useAutofocus();

        this.title = this.env._t("New Page");
        this.primaryTitle = this.env._t("Create");
        this.switchLabel = this.env._t("Add to menu");
        this.website = useService('website');
        this.orm = useService('orm');
        this.http = useService('http');
        this.action = useService('action');

        this.state = useState({
            addMenu: true,
            name: '',
            websiteId: false,
        });

        onWillStart(async () => {
            const [currentWebsite] = await Promise.all([
                await this.orm.call('website', 'get_current_website'),
                this.website.fetchWebsites(),
            ]);
            this.state.websiteId = unslugHtmlDataObject(currentWebsite).id;
        });
    }

    onChangeAddMenu(value) {
        this.state.addMenu = value;
    }

    async addPage() {
        const params = {'add_menu': this.state.addMenu || '', csrf_token};
        const url = `/website/add/${encodeURIComponent(this.state.name)}`;
        const websiteId = parseInt(this.state.websiteId);
        if (this.props.selectWebsite) {
            params['website_id'] = websiteId;
        }
        const data = await this.http.post(url, params);
        if (data.view_id) {
            this.action.doAction({
                'res_model': 'ir.ui.view',
                'res_id': data.view_id,
                'views': [[false, 'form']],
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
            });
        } else {
            this.website.goToWebsite({path: data.url, edition: true, ...(this.props.selectWebsite && {websiteId})});
        }
        this.props.onAddPage(this.state);
    }
}
AddPageDialog.props = {
    close: Function,
    onAddPage: {
        type: Function,
        optional: true,
    },
    selectWebsite: {
        type: Boolean,
        optional: true,
    },
};
AddPageDialog.defaultProps = {
    onAddPage: NO_OP,
    selectWebsite: false,
};
AddPageDialog.components = {
    Switch,
    WebsiteDialog,
};
AddPageDialog.template = xml`
<WebsiteDialog
    title="title"
    primaryTitle="primaryTitle"
    primaryClick="() => this.addPage()"
    close="props.close">
    <div class="row gy-4">
        <label class="col-form-label col-md-3">
            Page Title
        </label>
        <div class="col-md-9">
            <input type="text" t-model="state.name" class="form-control" required="required" t-ref="autofocus"/>
        </div>
        <t t-if="props.selectWebsite">
            <label class="col-form-label col-md-3">Website</label>
            <div class="col-md-9">
                <select class="form-select" t-model="state.websiteId">
                    <option t-foreach="website.websites"
                        t-as="option"
                        t-key="option.id"
                        t-att-value="option.id"
                        t-esc="option.name"
                    />
                </select>
            </div>
        </t>
        <Switch extraClasses="'offset-md-3 col-md-9 text-start'" label="switchLabel" value="state.addMenu" onChange="(value) => this.onChangeAddMenu(value)"/>
    </div>
</WebsiteDialog>
`;
