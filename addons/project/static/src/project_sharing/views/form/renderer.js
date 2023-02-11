/** @odoo-module **/

import FormRenderer from 'web.FormRenderer';
import Chatter from '@project/project_sharing/components/chatter';
import { session } from '@web/session';

export default FormRenderer.extend({
    _makeChatterContainerComponent() {
        const props = this._makeChatterContainerProps();
        this._chatterContainerComponent = new Chatter(this, props);
    },
    _makeChatterContainerProps() {
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
    _makeChatterContainerTarget() {
        const $el = $('<div class="o_FormRenderer_chatterContainer"/>');
        this._chatterContainerTarget = $el[0];
        return $el;
    },
    _mountChatterContainerComponent() {
        this._chatterContainerComponent.appendTo(this._chatterContainerTarget);
    },
    _renderNode(node) {
        if (node.tag === 'div' && node.attrs.class === 'oe_project_sharing_chatter') {
            let isVisible = true;
            if (node.attrs.modifiers && node.attrs.modifiers.invisible) {
                const record = this._getRecord(this.state.id);
                if (record) {
                    isVisible = !record.evalModifiers(node.attrs.modifiers).invisible;
                }
            }
            if (isVisible) {
                if (this._isFromFormViewDialog) {
                    return $('<div/>');
                }
                return this._makeChatterContainerTarget();
            }
        }
        return this._super(...arguments);
    },
});
