// @ts-check

/** @module @web/views/view_button/multi_record_view_button - ViewButton variant for list/kanban headers that operates on multiple selected records */

import { ViewButton } from "./view_button";

/** ViewButton variant for list/kanban headers that operates on multiple selected records at once. */
export class MultiRecordViewButton extends ViewButton {
    static props = [...ViewButton.props, "list", "domain"];

    /**
     * Resolve all selected record IDs from the list and inject active_domain/active_ids
     * into the button context before delegating to the environment handler.
     * @param {MouseEvent} ev
     * @param {boolean} [newWindow]
     */
    async onClick(ev, newWindow) {
        const { clickParams, list } = this.props;
        const resIds = await list.getResIds(true);
        clickParams.buttonContext = {
            active_domain: this.props.domain,
            active_ids: resIds,
            active_model: list.resModel,
        };

        return this.env.onClickViewButton({
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
