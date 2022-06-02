/** @odoo-module **/

import { useAutofocus } from '@web/core/utils/hooks';
import { Dialog } from '@web/core/dialog/dialog';
import { Switch } from '@website/components/switch/switch';
import { _t } from 'web.core';

const { xml, useState, Component } = owl;

const NO_OP = () => {};

export class WebsiteDialog extends Component {
    async primaryClick() {
        if (this.props.primaryClick) {
            await this.props.primaryClick();
        }
        if (this.props.closeOnClick) {
            this.props.close();
        }
    }

    async secondaryClick() {
        if (this.props.secondaryClick) {
            await this.props.secondaryClick();
        }
        if (this.props.closeOnClick) {
            this.props.close();
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

        this.state = useState({
            addMenu: true,
            name: '',
        });
    }

    onChangeAddMenu(value) {
        this.state.addMenu = value;
    }

    async addPage() {
        await this.props.addPage(this.state.name, this.state.addMenu);
    }
}
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
    <div class="form-group row">
        <label class="col-form-label col-md-3">
            Page Title
        </label>
        <div class="col-md-9">
            <input type="text" t-model="state.name" class="form-control" required="required" t-ref="autofocus"/>
        </div>
    </div>
    <Switch extraClasses="'offset-md-3 col-md-9 text-left'" label="switchLabel" value="state.addMenu" onChange="(value) => this.onChangeAddMenu(value)"/>
</WebsiteDialog>
`;
