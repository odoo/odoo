/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useAutofocus, useService } from "@web/core/utils/hooks";
import { sprintf } from "@web/core/utils/strings";

const { Component, useState } = owl;
const favoriteMenuRegistry = registry.category("favoriteMenu");

/**
 * 'Add to board' menu
 *
 * Component consisiting of a toggle button, a text input and an 'Add' button.
 * The first button is simply used to toggle the component and will determine
 * whether the other elements should be rendered.
 * The input will be given the name (or title) of the view that will be added.
 * Finally, the last button will send the name as well as some of the action
 * properties to the server to add the current view (and its context) to the
 * user's dashboard.
 * This component is only available in actions of type 'ir.actions.act_window'.
 * @extends Component
 */
export class AddToBoard extends Component {
    setup() {
        this.notification = useService("notification");
        this.rpc = useService("rpc");
        this.state = useState({ name: this.env.searchModel.displayName });

        useAutofocus();
    }

    //---------------------------------------------------------------------
    // Protected
    //---------------------------------------------------------------------

    async addToBoard() {
        const {
            action,
            displayName,
            domain,
            comparison,
            context,
            groupBy,
            orderedBy,
            view
        } = this.env.searchModel;

        // Retrieves view context
        const fns = this.env.__saveParams__.callbacks;
        const { context: viewContext } = Object.assign({}, ...fns.map((fn) => fn()));

        const contextToSave = {
            ...context,
            group_by: groupBy,
            orderedBy,
            dashboard_merge_domains_contexts: false,
            ...viewContext,
        };

        if (comparison) {
            contextToSave.comparison = comparison;
        }

        const result = await this.rpc("/board/add_to_dashboard", {
            action_id: action.id,
            context_to_save: contextToSave,
            domain,
            name: this.state.name,
            view_mode: view.type,
        });

        if (result) {
            this.notification.add(
                this.env._t("Please refresh your browser for the changes to take effect."),
                {
                    title: sprintf(this.env._t(`"%s" added to dashboard`), this.state.name),
                    type: "warning",
                }
            );
            this.state.name = displayName;
        } else {
            this.notification.add(
                this.env._t("Could not add filter to dashboard"),
                { type: "danger" }
            );
        }
    }

    //---------------------------------------------------------------------
    // Handlers
    //---------------------------------------------------------------------

    /**
     * @param {KeyboardEvent} ev
     */
    onInputKeydown(ev) {
        if (ev.key === "Enter") {
            ev.preventDefault();
            this.addToBoard();
        }
    }
}

AddToBoard.template = "board.AddToBoard";

const addToBoardItem = {
    Component: AddToBoard,
    isDisplayed: ({ searchModel }) => searchModel.action.type === "ir.actions.act_window",
};

favoriteMenuRegistry.add("add-to-board", addToBoardItem, { sequence: 10 });
