/** @odoo-module */

import { ViewButton } from "./view_button";

export class MultiRecordViewButton extends ViewButton {
    static props = [
        ...ViewButton.props,
        "list",
        "domain",
        "appliesToSelectedRecords?",
    ]
    static defaultProps = {
        ...ViewButton.defaultProps,
        appliesToSelectedRecords: true,
    }

    async onClick() {
        const { appliesToSelectedRecords, clickParams, list } = this.props;
        const resIds = await list.getResIds(appliesToSelectedRecords);
        clickParams.buttonContext = {
            active_domain: this.props.domain,
            active_ids: resIds,
            active_model: list.resModel,
        };

        this.env.onClickViewButton({
            clickParams,
            getResParams: () => ({
                context: list.context,
                evalContext: list.evalContext,
                resModel: list.resModel,
                resIds,
            }),
        });
    }
}
