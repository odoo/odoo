/** @odoo-module **/

import { ComponentWrapper } from 'web.OwlCompatibility';

export const RightPanelRendererMixin = {
    /**
     * Add RightPanel css class to renderer in order to handle panel style.
     *
     * @override
     */
    async start() {
        this.$el.addClass('o_renderer_with_rightpanel');
        await Promise.all([this._render(), this._super()]);
    },
};

export const RightPanelControllerMixin = {
    rightPanelPosition: 'last-child',
    /**
     * Init the rightSidePanel from the config parameters
     *
     * @override
     */
    init: function (parent, model, renderer, params) {
        this._super.apply(this, arguments);
        this.rightSidePanel = params.rightSidePanel;
    },
    /**
     * Add the Rightpanel component through the component wrapper.
     *
     * @override
     */
    start: async function () {
        const promises = [this._super(...arguments)];
        this._rightPanelWrapper = new ComponentWrapper(this, this.rightSidePanel.Component, this.rightSidePanel.props);
        const content = this.el.querySelector(':scope .o_content');
        content.classList.add('o_controller_with_rightpanel');
        promises.push(this._rightPanelWrapper.mount(content, { position: this.rightPanelPosition }));
        await Promise.all(promises);
    },
    /**
     * Make sure the right panel is updated each time the view is reloaded.
     *
     * @override
     */
    async _update() {
        this._rightPanelWrapper.update(this.rightSidePanel.props);
        await this._super.apply(this, arguments);
    },
};

export const RightPanelViewMixin = {
    searchMenuTypes: ['filter', 'favorite'],
    /**
     * Adds the rightSidePanel in the view.
     * This extention is assuming the rightSidePanel is always given in the case this Mixin is used.
     *
     * @override
     */
    _createSearchModel: function (params) {
        const result = this._super.apply(this, arguments);
        const props = {
            action: params.action,
        };
        this.controllerParams.rightSidePanel = {
            Component: this.config.RightSidePanel,
            props: props,
        };
        return result;
    }
};
