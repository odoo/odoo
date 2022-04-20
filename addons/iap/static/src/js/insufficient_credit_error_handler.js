/** @odoo-module */
import { Dialog } from "@web/core/dialog/dialog";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const { Component, onWillStart } = owl;

class InsufficientCreditDialog extends Component {
    setup() {
        this.orm = useService("orm");
        onWillStart(this.onWillStart);
    }

    async onWillStart() {
        const { errorData } = this.props;
        this.url = await this.orm.call("iap.account", "get_credits_url", [], {
            base_url: errorData.base_url,
            service_name: errorData.service_name,
            credit: errorData.credit,
            trial: errorData.trial,
        });
        this.style = errorData.body ? "padding:0;" : "";
        const { _t } = this.env;
        const { isEnterprise } = odoo.info;
        if (errorData.trial && isEnterprise) {
            this.buttonMessage = _t("Start a Trial at Odoo");
        } else {
            this.buttonMessage = _t("Buy credits");
        }
    }

    buyCredits() {
        window.open(this.url, "_blank");
        this.props.close();
    }
}
InsufficientCreditDialog.components = { Dialog };
InsufficientCreditDialog.template = "iap.InsufficientCreditDialog";

function insufficientCreditHandler(env, error, originalError) {
    if (!originalError) {
        return false;
    }
    const { data } = originalError;
    if (data && data.name === "odoo.addons.iap.tools.iap_tools.InsufficientCreditError") {
        env.services.dialog.add(InsufficientCreditDialog, {
            errorData: JSON.parse(data.message),
        });
        return true;
    }
    return false;
}

registry
    .category("error_handlers")
    .add("insufficientCreditHandler", insufficientCreditHandler, { sequence: 0 });
