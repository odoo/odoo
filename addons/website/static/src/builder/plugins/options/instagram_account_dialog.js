import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { Component, proxy, useProps, t } from "@odoo/owl";

export class InstagramAccountDialog extends Component {
    static template = "website.InstagramAccountDialog";
    static components = { Dialog };
    props = useProps({
        onConnect: t.function(),
        close: t.function(),
    });

    setup() {
        this.orm = useService("orm");
        this.state = proxy({ accessToken: "", error: "", isConnecting: false });
    }

    async onClickConnect() {
        this.state.isConnecting = true;
        const accountId = await this.orm.call("website.instagram.account", "connect", [
            this.state.accessToken,
        ]);
        this.state.isConnecting = false;
        if (accountId) {
            this.props.onConnect(accountId);
            this.props.close();
        } else {
            this.state.error = _t("Instagram did not accept this access token.");
        }
    }
}
