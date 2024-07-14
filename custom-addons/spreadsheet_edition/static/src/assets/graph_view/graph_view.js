/** @odoo-module **/

import { registry } from "@web/core/registry";
import { GraphRenderer } from "@web/views/graph/graph_renderer";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { SpreadsheetSelectorDialog } from "@spreadsheet_edition/assets/components/spreadsheet_selector_dialog/spreadsheet_selector_dialog";
import { omit } from "@web/core/utils/objects";

import { onWillStart } from "@odoo/owl";

export const patchGraphSpreadsheet = () => ({
    setup() {
        super.setup(...arguments);
        this.userService = useService("user");
        this.notification = useService("notification");
        this.actionService = useService("action");
        this.router = useService("router");
        this.menu = useService("menu");
        onWillStart(async () => {
            const insertionGroups = registry.category("spreadsheet_view_insertion_groups").getAll();
            const userGroups = await Promise.all(
                insertionGroups.map((group) => this.userService.hasGroup(group))
            );
            this.canInsertChart = userGroups.some((group) => group);
        });
    },

    async onInsertInSpreadsheet() {
        let menuXMLId = undefined;
        const menuId = this.router.current.hash.menu_id;
        if (menuId) {
            const menu = this.menu.getMenu(menuId);
            menuXMLId = menu ? menu.xmlid || menu.id : undefined;
        }
        const actionOptions = {
            preProcessingAsyncAction: "insertChart",
            preProcessingAsyncActionData: {
                metaData: this.model.metaData,
                searchParams: {
                    ...this.model.searchParams,
                    domain: this.env.searchModel.domainString,
                    context: omit(
                        this.model.searchParams.context,
                        ...Object.keys(this.userService.context),
                        "graph_measure",
                        "graph_order"
                    ),
                },
                menuXMLId,
            },
        };
        const params = {
            type: "GRAPH",
            name: this.model.metaData.title,
            actionOptions,
        };
        this.env.services.dialog.add(SpreadsheetSelectorDialog, params);
    },
});

/**
 * This patch is a little trick, which require a little explanation:
 *
 * In this patch, we add some dependencies to the graph view (menu service,
 * router service, ...).
 * To test it, we add these dependencies in our tests, but these dependencies
 * are not added in the tests of the base graph view (in web/). The same thing
 * occurs for the button "Insert in spreadsheet".
 * As we do not want to modify tests in web/ in order to integrate a behavior
 * defined in another module, we disable this patch in a file that is only
 * loaded in test assets (disable_patch.js), and re-active it in our tests.
 */
export const unpatchGraphSpreadsheet = patch(GraphRenderer.prototype, patchGraphSpreadsheet());
