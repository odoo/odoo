/** @odoo-module */

import { useModels } from '@mail/component_hooks/use_models';
import { ChatterContainer } from "@mail/components/chatter_container/chatter_container";
import { WebClientViewAttachmentViewContainer } from '@mail/components/web_client_view_attachment_view_container/web_client_view_attachment_view_container';

import { patch } from "@web/core/utils/patch";
import { FormRenderer } from "@web/views/form/form_renderer";

patch(FormRenderer.prototype, 'mail', {
    setup() {
        this._super();
        if (this.env.services.messaging) {
            useModels();
        }
    },

    get compileParams() {
        return {
            ...this._super(),
            hasAttachmentViewer: this.props.hasAttachmentViewer,
        };
    },

    //--------------------------------------------------------------------------
    // Mail Methods
    //--------------------------------------------------------------------------

    /**
     * @returns {Messaging|undefined}
     */
    getMessaging() {
        return this.env.services.messaging && this.env.services.messaging.modelManager.messaging;
    },
    /**
     * @returns {boolean}
     */
    hasAttachmentViewer() {
        if (!this.getMessaging() || !this.props.record.resId) {
            return false;
        }
        const thread = this.getMessaging().models['Thread'].insert({
            id: this.props.record.resId,
            model: this.props.record.resModel,
        });
        return (
            thread.attachmentsInWebClientView.length > 0
        );
    },
});

Object.assign(FormRenderer.components, {
    ChatterContainer,
    WebClientViewAttachmentViewContainer,
});
