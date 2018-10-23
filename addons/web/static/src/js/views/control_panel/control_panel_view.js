odoo.define('web.ControlPanelMixin', function (require) {
"use strict";

/**
 * Mixin allowing widgets to communicate with the ControlPanel. Widgets needing a
 * ControlPanel should use this mixin and call update_control_panel(cp_status) where
 * cp_status contains information for the ControlPanel to update itself.
 *
 * Note that the API is slightly awkward.  Hopefully we will improve this when
 * we get the time to refactor the control panel.
 *
 * For example, here is what a typical client action would need to do to add
 * support for a control panel with some buttons::
 *
 *     var ControlPanelMixin = require('web.ControlPanelMixin');
 *
 *     var SomeClientAction = Widget.extend(ControlPanelMixin, {
 *         ...
 *         start: function () {
 *             this._renderButtons();
 *             this._updateControlPanel();
 *             ...
 *         },
 *         do_show: function () {
 *              ...
 *              this._updateControlPanel();
 *         },
 *         _renderButtons: function () {
 *             this.$buttons = $(QWeb.render('SomeTemplate.Buttons'));
 *             this.$buttons.on('click', ...);
 *         },
 *         _updateControlPanel: function () {
 *             this.update_control_panel({
 *                 cp_content: {
 *                    $buttons: this.$buttons,
 *                 },
 *          });
 */
var ControlPanelMixin = {
    need_control_panel: true,
    /**
     * @param {web.ControlPanel} [cp]
     */
    set_cp: function (cp) {
        this._controlPanel = cp;
    },
    /**
     * @param {Object} [cp_status] see web.ControlPanel.update() for a description
     * @param {Object} [options] see web.ControlPanel.update() for a description
     */
    update_control_panel: function (cp_status, options) {
        if (this._controlPanel) {
            this._controlPanel.update(cp_status || {}, options || {});
        }
    },
};

return ControlPanelMixin;

});

odoo.define('web.ControlPanelView', function (require) {
"use strict";

var AbstractView = require('web.AbstractView');
var ControlPanelController = require('web.ControlPanelController');
var ControlPanelModel = require('web.ControlPanelModel');
var ControlPanelRenderer = require('web.ControlPanelRenderer');

var ControlPanelView = AbstractView.extend({
    config: {
        Controller: ControlPanelController,
        Model: ControlPanelModel,
        Renderer: ControlPanelRenderer,
    },
    viewType: 'controlpanel',

    /**
     * @override
     * @param {string} [params.template] the QWeb template to render
     */
    init: function (viewInfo, params) {
        viewInfo = viewInfo || {arch: {attrs: {}}, fields: {}};
        params = params || {};
        params.context = {};
        this._super(viewInfo, params);

        if (this.arch.tag === 'controlpanel') {
            this._parseControlPanelArch();
        } else {
            this._parseSearchArch();
        }

        this.rendererParams.controls = this.controls;
        this.rendererParams.template = params.template;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Executed when the given arch has root node <controlpanel>.
     *
     * @private
     */
    _parseControlPanelArch: function () {
        var controls = [];
        this.arch.children.forEach(function (node) {
            if (node.tag === 'controls') {
                node.children.forEach(function (control) {
                    controls.push(control);
                });
            }
        });
        this.controls = controls;
    },
    /**
     * Executed when the given arch has root node <search>, for backward
     * compatibility with former 'search' view.
     *
     * @todo: put dam and ged's branch code of SearchView here
     *
     * @private
     */
    _parseSearchArch: function () {

    },
});

return ControlPanelView;

});
