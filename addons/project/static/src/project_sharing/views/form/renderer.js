/** @odoo-module **/

import FormRenderer from 'web.FormRenderer';
import { PortalChatter } from 'portal.chatter';

export default FormRenderer.extend({
    _makeChatterContainerComponent() {
        const props = this._makeChatterContainerProps();
        this._chatterContainerComponent = new PortalChatter(this, props);
    },
    _makeChatterContainerProps() {
        return {
            token: '',
            res_model: 'project.task',
            pid: '',
            hash: '',
            res_id: this.state.res_id,
            pager_step: 10,
            allow_composer: true,
            two_columns: false,
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
    _updateChatterContainerComponent() {},
});
