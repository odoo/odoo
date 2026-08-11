import { t, useProps } from "@odoo/owl";
import { ViewButton, viewButtonProps } from "./view_button";
import { useViewButtonHandler } from "@web/views/view_button/view_button_hook";

export class MultiRecordViewButton extends ViewButton {
    props = useProps({
        ...viewButtonProps,
        list: t.any(),
        domain: t.any(),
    });

    handleViewButton = useViewButtonHandler();

    async onClick(ev, newWindow) {
        const { clickParams, list } = this.props;
        const resIds = await list.getResIds(true);
        clickParams.buttonContext = {
            active_domain: this.props.domain,
            active_ids: resIds,
            active_model: list.resModel,
        };

        this.handleViewButton({
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
