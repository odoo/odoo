// @ts-check
/** @odoo-module native */

import { Component, onWillStart, onWillUpdateProps, useState } from "@odoo/owl";
import { Dropdown } from "@web/components/dropdown/dropdown";
import { DropdownItem } from "@web/components/dropdown/dropdown_item";
import { useAction } from "@web/core/action_port";
import { browser } from "@web/core/browser/browser";
import { makeContext } from "@web/core/context";
import { _t } from "@web/core/translation";
import { KeepLast, SupersededError } from "@web/core/utils/concurrency";
import { useService } from "@web/core/utils/hooks";
import { COG_GROUP } from "@web/search/cog_menu/cog_menu_group";
import { CogMenuItem } from "@web/search/cog_menu/cog_menu_item";
import { session } from "@web/session";

export class ActionMenus extends Component {
    static template = "web.ActionMenus";
    static components = {
        CogMenuItem,
        Dropdown,
        DropdownItem,
    };
    static props = {
        getActiveIds: Function,
        context: Object,
        resModel: String,
        printDropdownTitle: { type: String, optional: true },
        domain: { type: Array, optional: true },
        isDomainSelected: { type: Boolean, optional: true },
        items: {
            type: Object,
            shape: {
                action: { type: Array, optional: true },
                print: { type: Array, optional: true },
            },
        },
        onActionExecuted: { type: Function, optional: true },
        shouldExecuteAction: { type: Function, optional: true },
        loadExtraPrintItems: { type: Function, optional: true },
    };
    static defaultProps = {
        printDropdownTitle: _t("Print"),
        onActionExecuted: () => {},
        shouldExecuteAction: () => true,
        loadExtraPrintItems: () => /** @type {any[]} */ ([]),
    };

    setup() {
        this.orm = useService("orm");
        this.actionService = useAction();
        this.state = useState({ printItems: [] });
        this.keepLast = new KeepLast({ rejectSuperseded: true });
        onWillStart(async () => {
            this.actionItems = await this.getActionItems(this.props);
        });
        onWillUpdateProps(async (nextProps) => {
            this.actionItems = await this.getActionItems(nextProps);
        });
    }

    /**
     * @param {Record<string, any>} props
     * @returns {Promise<Array<{key: string, groupNumber: number, description?: string, action?: Record<string, any>, callback?: Function}>>}
     */
    async getActionItems(props) {
        return (props.items.action || [])
            .map((/** @type {any} */ action) => {
                if (action.callback) {
                    return Object.assign(
                        {
                            key: `action-${action.description}`,
                            groupNumber: COG_GROUP.ACTIONS,
                        },
                        action,
                    );
                } else {
                    return {
                        action,
                        description: action.name,
                        icon: action.binding_icon || undefined,
                        key: action.id,
                        groupNumber: action.groupNumber || COG_GROUP.ACTIONS,
                    };
                }
            })
            .toSorted(
                (/** @type {any} */ item1, /** @type {any} */ item2) =>
                    item1.groupNumber - item2.groupNumber,
            );
    }

    /**
     * @param {{ id: number, name: string }} action
     * @returns {Promise<number|void>}
     */
    async executeAction(action) {
        let activeIds = this.props.getActiveIds();
        if (this.props.isDomainSelected) {
            activeIds = await this.orm.search(this.props.resModel, this.props.domain, {
                limit: session.active_ids_limit,
                context: this.props.context,
            });
        }
        /** @type {Record<string, any>} */
        const activeIdsContext = {
            active_id: activeIds[0],
            active_ids: activeIds,
            active_model: this.props.resModel,
        };
        if (this.props.domain) {
            activeIdsContext.active_domain = this.props.domain;
        }
        const context = makeContext([this.props.context, activeIdsContext]);
        return this.actionService.doAction(action.id, {
            additionalContext: context,
            onClose: this.props.onActionExecuted,
        });
    }

    /**
     * @private
     * @param {Record<string, any>} item
     */
    async onItemSelected(item) {
        if (!(await this.props.shouldExecuteAction(item))) {
            return;
        }
        if (item.callback) {
            item.callback([item]);
        } else if (item.action) {
            this.executeAction(item.action);
        } else if (item.url) {
            browser.location.href = item.url;
        }
    }

    /** @returns {Promise<Array<{action: Object, class: string, description: string, key: number}>>} */
    async loadAvailablePrintItems() {
        const printActions = this.props.items.print || [];
        /** @type {number[]} */
        const actionWithDomainIds = [];
        /** @type {number[]} */
        const validActionIds = [];
        for (const action of printActions) {
            "domain" in action
                ? actionWithDomainIds.push(action.id)
                : validActionIds.push(action.id);
        }
        if (actionWithDomainIds.length) {
            const validActionsWithDomainIds = await this.orm.call(
                "ir.actions.report",
                "get_valid_action_reports",
                [actionWithDomainIds, this.props.resModel, this.props.getActiveIds()],
            );
            validActionIds.push(...validActionsWithDomainIds);
        }
        return printActions
            .filter((/** @type {any} */ action) => validActionIds.includes(action.id))
            .map((/** @type {any} */ action) => ({
                action,
                class: "o_menu_item",
                description: action.name,
                key: action.id,
            }));
    }

    async loadPrintItems() {
        if (!this.props.items.print?.length) {
            return;
        }
        let items;
        let extraItems;
        try {
            [items, extraItems] = await this.keepLast.add(
                Promise.all([
                    this.loadAvailablePrintItems(),
                    this.props.loadExtraPrintItems(),
                ]),
            );
        } catch (error) {
            if (error instanceof SupersededError) {
                return;
            }
            throw error;
        }
        const allItems = [...extraItems, ...items];
        if (!allItems.length) {
            allItems.push({
                description: _t("No report available."),
                class: "o_menu_item disabled",
                key: "nothing_to_display",
            });
        }
        this.state.printItems = allItems;
    }
}
