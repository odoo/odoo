import { useSetupAction } from "@web/search/action_hook";
import { onWillStart } from "@odoo/owl";

export function projectUpdateControllerStatePersistancePatch() {
    return {
        /**
         * @override
         */
        setup() {
            super.setup();
            this.prevSectionState = this.props?.state?.sectionState || {};
            useSetupAction({
                getGlobalState: () => {
                    const sectionState = {};
                    this.rootRef.el.querySelectorAll("tr td button.fa-caret-down").forEach((node) => {
                        const rowId = node.closest("tr").id;
                        const ids = Array.from(
                            this.rootRef.el.querySelectorAll(`#${rowId}-unfolded tbody tr`),
                            (val) => parseInt(val.id)
                        );
                        sectionState[rowId] = ids;
                    });
                    return { sectionState };
                },
            });
            onWillStart(async () => {
                if (this.props?.globalState?.sectionState) {
                    this.prevSectionState = await this.model.orm.call(
                        "project.project",
                        "prefetch_sale_items_data",
                        [this.props.context.active_id, this.props?.globalState?.sectionState]
                    );
                }
            });
        },
    };
}
