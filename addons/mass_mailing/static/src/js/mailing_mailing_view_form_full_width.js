/** @odoo-module **/

import FormView from 'web.FormView';
import FormRenderer from 'web.FormRenderer';
import viewRegistry from 'web.view_registry';
import config from 'web.config';

const MassMailingFullWidthFormRenderer = FormRenderer.extend({
    /**
     * Overload the rendering of the header in order to add a child to it: move
     * the alert after the statusbar.
     *
     * @private
     * @override
     */
    _renderTagHeader: function (node) {
        const $statusbar = this._super(...arguments);
        const alert = node.children.find(child => child.tag === "div" && child.attrs.role === "alert");
        const $alert = this._renderGenericTag(alert);
        $statusbar.find('.o_statusbar_buttons').after($alert);
        return $statusbar;
    },
    /**
     * Increase the default number of button boxes before folding since the form
     * without sheet is a lot bigger and more space is available for them.
     *
     * @private
     * @override
     */
    _renderButtonBoxNbButtons: function () {
        return [2, 2, 2, 4, 6, 7][config.device.size_class] || 10;
    },
});

export const MassMailingFullWidthFormView = FormView.extend({
    config: Object.assign({}, FormView.prototype.config, {
        Renderer: MassMailingFullWidthFormRenderer,
    }),
});

viewRegistry.add('mailing_mailing_view_form_full_width', MassMailingFullWidthFormView);
