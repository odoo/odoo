import { Component, onWillStart, proxy, props, types as t } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

class IapContainer extends Component {
    static template = "mysubscription.IapContainer";

    props = props({
        account: t.object({
            action: t.object(),
            balance: t.string(),
            credit_url: t.string(),
            data: t.string(),
            description: t.string(),
            name: t.string(),
            service_name: t.string(),
        })
    });

    setup() {
        this.actionService = useService("action");
        this.state = proxy({ isHovered: null });
    }

    openSettings() {
        const actionDict = this.props.account.action;
        if (!actionDict.views) {
            actionDict.views = [[false, "form"]];
        }
        this.actionService.doAction(actionDict);
    }

    get name() {
        return this.props.account.name;
    }

    get balance() {
        return this.props.account.balance;
    }

    get creditUrl() {
        return this.props.account.credit_url;
    }

    get description() {
        return this.props.account.description;
    }

    get imageUrl() {
        const service = this.props.account.service_name;
        const existingIcon = ["sms", "reveal", "snailmail", "partner_autocomplete", "invoice_ocr"];
        if (existingIcon.includes(service)) {
            return `/mysubscription/static/src/img/${service}_icon.png`;
        }
        return "/mysubscription/static/src/img/default_iap_icon.png";
    }

    openTopUp() {
        window.open(this.creditUrl, "_blank");
    }
}

export class IapSection extends Component {
    static template = "mysubscription.IapSection";
    static components = {
        IapContainer,
    };

    setup() {
        this.orm = useService("orm");

        onWillStart(async () => {
            this.iapAccounts = await this.loadIap();
        });
    }

    async loadIap() {
        const configData = await this.orm.call(
            "mysubscription.mysubscription",
            "get_iap_data",
            []
        );
        return configData;
    }

}
