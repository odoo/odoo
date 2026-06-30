import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class ImportDataColumnError extends Component {
    static template = "ImportDataColumnError";
    static props = {
        errors: { type: Array },
        fieldInfo: { type: Object },
        resultNames: { type: Array },
    };

    setup() {
        this.action = useService("action");
        this.orm = useService("orm");
        this.state = useState({
            isExpanded: false,
            moreInfoContent: undefined,
        });
    }
    get moreInfo() {
        const moreInfoObjects = this.props.errors.map((error) => error.moreinfo);
        return moreInfoObjects.length && moreInfoObjects[0];
    }
    isErrorVisible(index) {
        return this.state.isExpanded || index < 3;
    }
    onMoreInfoClicked() {
        const moreInfo = this.moreInfo;
        if (this.state.moreInfoContent) {
            this.state.moreInfoContent = undefined;
        } else if (moreInfo instanceof Array) {
            this.state.moreInfoContent = moreInfo;
        } else {
            this.action.doAction(moreInfo);
        }
    }
}
