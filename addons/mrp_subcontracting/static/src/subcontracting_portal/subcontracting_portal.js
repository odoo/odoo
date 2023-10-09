/** @odoo-module **/

import { useService } from '@web/core/utils/hooks';
import { ActionContainer } from '@web/webclient/actions/action_container';
import { MainComponentsContainer } from "@web/core/main_components_container";
import { useOwnDebugContext } from "@web/core/debug/debug_context";
import { session } from '@web/session';
import { Component, useEffect, useExternalListener } from "@odoo/owl";

export class SubcontractingPortalWebClient extends Component {
    setup() {
        window.parent.document.body.style.margin = "0"; // remove the margin in the parent body
        this.actionService = useService('action');
        this.user = useService("user");
        useOwnDebugContext({ categories: ["default"] });
        useEffect(
            () => {
                this._showView();
            },
            () => []
        );
        useExternalListener(window, "click", this.onGlobalClick, { capture: true });
    }

    async _showView() {
        const { action_name, picking_id } = session;
        await this.actionService.doAction(
            action_name,
            {
                props: {
                    resId: picking_id,
                    preventEdit: true,
                    preventCreate: true,
                },
                additionalContext: {
                    no_breadcrumbs: true,
                }
            }
        );
    }

    /**
     * @param {MouseEvent} ev
     */
     onGlobalClick(ev) {
        // When a ctrl-click occurs inside an <a href/> element
        // we let the browser do the default behavior and
        // we do not want any other listener to execute.
        if (
            ev.ctrlKey &&
            ((ev.target instanceof HTMLAnchorElement && ev.target.href) ||
                (ev.target instanceof HTMLElement && ev.target.closest("a[href]:not([href=''])")))
        ) {
            ev.stopImmediatePropagation();
            return;
        }
    }
}

SubcontractingPortalWebClient.components = { ActionContainer, MainComponentsContainer };
SubcontractingPortalWebClient.template = 'mrp_subcontracting.SubcontractingPortalWebClient';
