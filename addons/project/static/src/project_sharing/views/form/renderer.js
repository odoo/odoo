/** @odoo-module **/

import '@mail/widgets/form_renderer/form_renderer'; // ensure mail overrides are applied first

import FormRenderer from 'web.FormRenderer';
import Chatter from '@project/project_sharing/components/chatter';
import { session } from '@web/session';

export default FormRenderer.extend({
    /**
     * Creates the portal chatter instead of the standard chatter.
     *
     * This overridden method is expected to be called from proper lifecycle
     * method of mail form renderer, when `this._chatterContainerTarget` is set.
     *
     * @override
     */
    initChatter() {
        const options = this.makePortalChatterOptions();
        this.portalChatter = new Chatter(this, options);
        this.portalChatter.appendTo(this._chatterContainerTarget);
    },
    /**
     * Updates the options of the portal chatter instead of the props of the
     * standard chatter.
     *
     * This overridden method is expected to be called from proper lifecycle
     * method of mail form renderer.
     *
     * @override
     */
    _updateChatterContainerComponent() {
        const options = this.makePortalChatterOptions();
        this.portalChatter.update(options);
    },
    makePortalChatterOptions() {
        // FIXME: perhaps check if we have a parent in the window ?
        // Call the parent window to get the url displayed in the browser since we are in an iframe
        const query = new URLSearchParams(window.parent.location.search);
        return {
            token: query.get('access_token') || '',
            res_model: 'project.task',
            pid: '',
            hash: '',
            res_id: this.state.res_id,
            pager_step: 10,
            allow_composer: !!this.state.res_id,
            two_columns: false,
            project_sharing_id: session.project_id,
        };
    },
});
