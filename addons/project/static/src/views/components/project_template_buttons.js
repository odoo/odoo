import { Component, t, useProps } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog, deleteConfirmationMessage } from "@web/core/confirmation_dialog/confirmation_dialog";
import { localization } from "@web/core/l10n/localization";

const isRTL = () => localization.direction === "rtl";
const isRowAction = (item) => Boolean(item?.el.closest(".o_template_icon_group"));
const rowsOf = (navigator) => navigator.items.filter((item) => !isRowAction(item));

/** Activates the next row in the `step` direction, skipping the rows' actions. */
function moveToRow(navigator, step) {
    const move = step > 0 ? () => navigator.next() : () => navigator.previous();
    for (let i = 0; i < navigator.items.length; i++) {
        move();
        if (!isRowAction(navigator.activeItem)) {
            return;
        }
    }
}

/** Steps into the actions of the active row, and back out of them. */
function moveWithinRow(navigator, step) {
    const { items, activeItemIndex } = navigator;
    const target = items[activeItemIndex + step];
    if (activeItemIndex < 0 || !target) {
        return;
    }
    // Stepping in has to land on an action, stepping out has to start from one,
    // which is what keeps a row from reaching its neighbour's actions.
    if (isRowAction(step > 0 ? target : items[activeItemIndex])) {
        target.setActive();
    }
}

// The hotkeys are given as objects so that deepMerge keeps the flags the
// framework sets on them.
export const templateButtonsNavigationOptions = {
    // false: the default would target each row's first nested <button> (the edit
    // icon), so Enter would open the template instead of using it.
    shouldFocusChildInput: false,
    hotkeys: {
        // Up and down walk the rows, left and right reach the actions of a row.
        // Tab is left alone, so it still steps through every item.
        arrowdown: { callback: (navigator) => moveToRow(navigator, 1) },
        arrowup: { callback: (navigator) => moveToRow(navigator, -1) },
        arrowright: { callback: (navigator) => moveWithinRow(navigator, isRTL() ? -1 : 1) },
        arrowleft: { callback: (navigator) => moveWithinRow(navigator, isRTL() ? 1 : -1) },
        // Rows again, otherwise End would land on a row's last action.
        home: (navigator) => rowsOf(navigator)[0]?.setActive(),
        end: (navigator) => rowsOf(navigator).at(-1)?.setActive(),
        // Rebound because the rows are <span>, not <button>.
        space: (navigator) => navigator.activeItem?.select(),
    },
};

export class ProjectTemplateButtons extends Component {
    static template = "project.ProjectTemplateButtons";
    props = useProps({
        resModel: t.string(),
        resId: t.number(),
    });

    setup() {
        this.orm = useService("orm");
        this.dialogService = useService("dialog");
        this.action = useService("action");
    }

    onEditClick() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: this.props.resModel,
            res_id: this.props.resId,
            views: [[false, "form"]],
        });
    }

    async onDeleteClick() {
        this.dialogService.add(ConfirmationDialog, {
            body: deleteConfirmationMessage,
            confirm: async () => {
                await this.orm.unlink(this.props.resModel, [this.props.resId]);
                this.action.doAction("soft_reload");
            },
            cancel: () => {},
        });
    }
}
