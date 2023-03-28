/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { DomainSelectorDialog } from "@web/core/domain_selector_dialog/domain_selector_dialog";

export class AdvancedSearchDialog extends DomainSelectorDialog {
    get dialogTitle() {
        return _t("Advanced Search");
    }

    async onConfirm() {
        const confirmed = await this.props.onConfirm(this.state.domain);
        if (confirmed) {
            this.props.close();
        }
    }
}
AdvancedSearchDialog.template = "web.AdvancedSearchDialog";
