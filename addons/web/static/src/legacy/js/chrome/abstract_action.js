/** @odoo-module alias=web.AbstractAction **/

/**
 * We define here the AbstractAction widget, which implements the ActionMixin.
 * All client actions must extend this widget.
 *
 * @module @web/chrome/abstract_action
 */

import ActionMixin from "web.ActionMixin";
import ControlPanel from "web.ControlPanel";
import Widget from "web.Widget";
import { ComponentWrapper } from "web.OwlCompatibility";

const AbstractAction = Widget.extend(ActionMixin, {
    config: {
        ControlPanel: ControlPanel,
    },

    /**
     * If this flag is set to true, the client action will create a control
     * panel whenever it is created.
     *
     * @type boolean
     */
    hasControlPanel: false,

    /**
     * @override
     *
     * @param {Widget} parent
     * @param {Object} action
     * @param {Object} [options]
     */
    init: function (parent, action, options) {
        this._super(parent);
        this._title = action.display_name || action.name;

        if (this.hasControlPanel) {
            this.controlPanelProps = {
                action,
                breadcrumbs: options && options.breadcrumbs,
            };
        }
    },
    /**
     * @override
     */
    start: async function () {
        await this._super(...arguments);
        if (this.hasControlPanel) {
            if ('title' in this.controlPanelProps) {
                this._setTitle(this.controlPanelProps.title);
            }
            this.controlPanelProps.title = this.getTitle();
            this._controlPanelWrapper = new ComponentWrapper(this, this.config.ControlPanel, this.controlPanelProps);
            await this._controlPanelWrapper.mount(this.el, { position: 'first-child' });

        }
    },
    /**
     * @override
     */
    destroy: function() {
        this._super.apply(this, arguments);
        ActionMixin.destroy.call(this);
    },
    /**
     * @override
     */
    on_attach_callback: function () {
        ActionMixin.on_attach_callback.call(this);
    },
    /**
     * @override
     */
    on_detach_callback: function () {
        ActionMixin.on_detach_callback.call(this);
    },
});

export default AbstractAction;
