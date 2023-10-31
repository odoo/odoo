/** @odoo-module **/

import { useBus, useEffect, useService } from '@web/core/utils/hooks';
import { ActionContainer } from '@web/webclient/actions/action_container';
import { MainComponentsContainer } from "@web/core/main_components_container";
import { useOwnDebugContext } from "@web/core/debug/debug_context";
import { ErrorHandler, NotUpdatable } from "@web/core/utils/components";
import { session } from '@web/session';

const { Component } = owl;

export class ProjectSharingWebClient extends Component {
    setup() {
        window.parent.document.body.style.margin = "0"; // remove the margin in the parent body
        this.actionService = useService('action');
        this.user = useService("user");
        useService("legacy_service_provider");
        useOwnDebugContext({ categories: ["default"] });
        useBus(this.env.bus, "ACTION_MANAGER:UI-UPDATED", (mode) => {
            if (mode !== "new") {
                this.el.classList.toggle("o_fullscreen", mode === "fullscreen");
            }
        });
        useEffect(
            () => {
                this._showView();
            },
            () => []
        );
    }

    mounted() { }

    handleComponentError(error, C) {
        // remove the faulty component
        this.Components.splice(this.Components.indexOf(C), 1);
        /**
         * we rethrow the error to notify the user something bad happened.
         * We do it after a tick to make sure owl can properly finish its
         * rendering
         */
        Promise.resolve().then(() => {
            throw error;
        });
    }

    async _showView() {
        const { action_name, project_id } = session;
        await this.actionService.doAction(
            action_name,
            {
                clearBreadcrumbs: true,
                additionalContext: {
                    active_id: project_id,
                }
            }
        );
    }
}

ProjectSharingWebClient.components = { ActionContainer, ErrorHandler, NotUpdatable, MainComponentsContainer };
ProjectSharingWebClient.template = 'project.ProjectSharingWebClient';
