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

    get uploadParams() {
        return this.getUploadParams(this.props.list);
    }

    async onClick(ev, newWindow) {
        const { clickParams, list } = this.props;
        // the files are uploaded, not given to the selected records, unless the
        // button is only shown for a selection (e.g. a bill for the selected orders)
        const ignoresSelection =
            clickParams.type === "upload" && this.props.attrs?.display !== "selection";
        const resIds = ignoresSelection ? [] : await list.getResIds(true);
        if (!ignoresSelection) {
            clickParams.buttonContext = {
                active_domain: this.props.domain,
                active_ids: resIds,
                active_model: list.resModel,
            };
        }

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
