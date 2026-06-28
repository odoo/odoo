import { props, t } from "@odoo/owl";
import { ViewButton, viewButtonProps } from "./view_button";

export class MultiRecordViewButton extends ViewButton {
    props = props({
        ...viewButtonProps,
        list: t.any(),
        domain: t.any(),
    });

    async onClick(ev, newWindow) {
        const { clickParams, list } = this.props;
        const resIds = await list.getResIds(true);
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
            newWindow,
        });
    }
}
