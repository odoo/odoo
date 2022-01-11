/** @odoo-module **/

import { Dialog } from '@web/core/dialog/dialog';
import { Switch } from '@website/components/switch/switch';

const { xml, useState } = owl;

export class WebsiteDialog extends Dialog {
    setup() {
        super.setup();
        this.title = this.props.title || this.env._t("Confirmation");
        this.primaryTitle = this.props.primaryTitle || this.env._t("Ok");
        this.secondaryTitle = this.props.secondaryTitle || this.env._t("Cancel");
        this.closeOnClick = this.props.closeOnClick === false ? false : true;
    }

    primaryClick() {
        if (this.props.primaryClick) {
            this.props.primaryClick();
        }
        if (this.closeOnClick) {
            this.close();
        }
    }

    secondaryClick() {
        if (this.props.secondaryClick) {
            this.props.secondaryClick();
        }
        if (this.closeOnClick) {
            this.close();
        }
    }
}
WebsiteDialog.props = {
    ...Dialog.props,
    title: { type: String, optional: true },
    body: { type: String, optional: true },
    primaryTitle: { type: String, optional: true },
    primaryClick: { type: Function, optional: true },
    secondaryTitle: { type: String, optional: true },
    secondaryClick: { type: Function, optional: true },
    closeOnClick: { type: Boolean, optional: true },
    close: { type: Function, optional: true },
};
WebsiteDialog.bodyTemplate = "website.DialogBody";
WebsiteDialog.footerTemplate = "website.DialogFooter";
WebsiteDialog.size = "modal-md";
WebsiteDialog.contentClass = "o_website_dialog";

export class AddPageDialog extends WebsiteDialog {
    setup() {
        super.setup();

        this.title = this.env._t("New Page");
        this.primaryTitle = this.env._t("Create");

        this.state = useState({
            addMenu: true,
            name: '',
        });
    }

    onChangeAddMenu(value) {
        this.state.addMenu = value;
    }

    async primaryClick() {
        await this.props.addPage(this.state.name, this.state.addMenu);
        this.close();
    }
}
AddPageDialog.props = {
    ...WebsiteDialog.props,
    addPage: Function,
};
AddPageDialog.components = {
    Switch,
};
AddPageDialog.bodyTemplate = xml`
<div>
    <div class="form-group row">
        <label class="col-form-label col-md-3">
            Page Title
        </label>
        <div class="col-md-9">
            <input type="text" t-model="state.name" class="form-control" required="required"/>
        </div>
    </div>
    <Switch extraClasses="'offset-md-3 col-md-9 text-left'" label="'Add to menu'" value="state.addMenu" onChange="(value) => this.onChangeAddMenu(value)"/>
</div>
`;
