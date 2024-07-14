/** @odoo-module */

import { AbstractBehavior } from "@knowledge/components/behaviors/abstract_behavior/abstract_behavior";
import { makeContext } from "@web/core/context";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { useEffect } from "@odoo/owl";


/**
 * Clickable "link" to access a view from an article with custom facets (only
 * usable in Odoo)
 */
export class ViewLinkBehavior extends AbstractBehavior {
    static props = {
        ...AbstractBehavior.props,
        action_xml_id: { type: String, optional: true },
        act_window: { type: Object, optional: true },
        context: { type: Object },
        name: { type: String },
        view_type: { type: String }
    };
    static template = "knowledge.ViewLinkBehavior";

    setup () {
        super.setup();
        this.actionService = useService('action');
        this.notification = useService("notification");
        this.userService = useService("user");
        useEffect(() => {
            const type = this.props.readonly ? 'click' : 'dblclick';
            /**
             * @param {Event} event
             */
            const onLinkClick = async (event) => {
                const isInternalUser = await this.userService.hasGroup("base.group_user");
                if (!isInternalUser) {
                    return this.notification.add(_t("Only Internal Users can access this view."), {
                        type: "warning",
                    });
                }
                this.openViewLink(event);
            };
            this.props.anchor.addEventListener(type, onLinkClick);
            return () => {
                this.props.anchor.removeEventListener(type, onLinkClick);
            };
        });
    }

    //--------------------------------------------------------------------------
    // HANDLERS
    //--------------------------------------------------------------------------

    /**
     * @param {Event} event
     */
    async openViewLink (event) {
        const action = await this.actionService.loadAction(
            this.props.act_window || this.props.action_xml_id,
            makeContext([this.props.context])
        );
        if (action.type !== "ir.actions.act_window") {
            throw new Error('Can not open the view: The action is not an "ir.actions.act_window"');
        }
        action.globalState = {
            searchModel: this.props.context.knowledge_search_model_state
        };
        const props = {};
        if (action.context.orderBy) {
            try {
                props.orderBy = JSON.parse(action.context.orderBy);
            } catch {};
        }
        this.actionService.doAction(action, {
            viewType: this.props.view_type,
            props
        });
    }
}
