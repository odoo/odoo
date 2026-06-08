import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { WebsiteDialog } from "@website/components/dialog/dialog";

export class InstallModuleDialog extends Component {
    static components = { WebsiteDialog };
    static template = "website.InstallModuleDialog";
    static props = {
        title: String,
        installationText: String,
        installModule: Function,
        close: Function,
    };

    setup() {
        this.installButtonTitle = _t("Install");
    }

    onClickInstall() {
        this.props.close();
        this.props.installModule();
    }
}
