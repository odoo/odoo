/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { useChildRef } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";

export class ExitSplitToolsDialog extends Component {
    static components = { Dialog };
    static props = {
        close: Function,
        isRuleApplied: Boolean,
        onDeleteRemainingPages: Function,
        onGatherRemainingPages: Function,
    };
    static template = "documents.ExitToolsDialog";

    setup() {
        this.modalRef = useChildRef();
        this.title = _t("Exit Split Tools");
    }
    /**
     * @public
     */
    deleteRemainingPages() {
        this.props.onDeleteRemainingPages();
        this.props.close();
    }
    /**
     * @public
     */
    gatherRemainingPages() {
        this.props.onGatherRemainingPages();
        this.props.close();
    }
}
