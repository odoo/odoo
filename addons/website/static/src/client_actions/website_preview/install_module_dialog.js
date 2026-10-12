import { Component, useProps, t } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { WebsiteDialog } from "@website/components/dialog/dialog";

export class InstallModuleDialog extends Component {
    static components = { WebsiteDialog };
    static template = "website.InstallModuleDialog";
    props = useProps({
        title: t.string(),
        installationText: t.string(),
        installModule: t.function(),
        close: t.function(),
    });

    setup() {
        this.installButtonTitle = _t("Install");
    }

    onClickInstall() {
        this.props.close();
        this.props.installModule();
    }
}
