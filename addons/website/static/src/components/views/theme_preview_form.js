odoo.define('website.theme_preview_form', function (require) {
"use strict";

var FormController = require('web.FormController');
var FormView = require('web.FormView');
var viewRegistry = require('web.view_registry');
var core = require('web.core');
var qweb = core.qweb;

/*
* Common code for theme installation/update handler.
*/
const ThemePreviewControllerCommon = {
    /**
     * Called to add loading effect and install/pdate the selected theme depending on action.
     *
     * @private
     * @param {number} res_id
     * @param {String} action
     */
    _handleThemeAction(res_id, action) {
        this.$loader = $(qweb.render('website.ThemePreview.Loader', {
            'showTips': action !== 'button_refresh_theme',
        }));
        let actionCallback = undefined;
        this._addLoader();
        switch (action) {
            case 'button_choose_theme':
                actionCallback = result => {
                    this.do_action(result);
                    this._removeLoader();
                };
                break;
            case 'button_refresh_theme':
                actionCallback = () => this._removeLoader();
                break;
        }
        const rpcData = {
            model: 'ir.module.module',
            method: action,
            args: [res_id],
            context: this.initialState.context,
        };
        const rpcOptions = {
            shadow: true,
        };
        this._rpc(rpcData, rpcOptions)
            .then(actionCallback)
            .guardedCatch(() => this._removeLoader());
    },
    /**
     * Called to add loader element in DOM.
     *
     * @private
     */
    _addLoader() {
        $('body').append(this.$loader);
    },
    /**
     * @private
     */
    _removeLoader() {
        this.$loader.remove();
    }
};

var ThemePreviewController = FormController.extend(ThemePreviewControllerCommon, {
    events: Object.assign({}, FormController.prototype.events, {
        'click .o_use_theme': '_onStartNowClick',
        'click .o_switch_theme': '_onSwitchThemeClick',
        'change input[name="viewer"]': '_onSwitchButtonChange',
    }),
    /**
     * @override
     */
    start: function () {
        this.$el.addClass('o_view_form_theme_preview_controller');
        return this._super.apply(this, arguments);
    },

    // -------------------------------------------------------------------------
    // Public
    // -------------------------------------------------------------------------

    /**
     * @override
     */
    renderButtons: function ($node) {
        this.$buttons = $(qweb.render('website.ThemePreview.Buttons'));
        if ($node) {
            $node.html(this.$buttons);
        }
    },
    /**
     * Overriden to prevent the controller from hiding the buttons
     * @see FormController
     *
     * @override
     */
    updateButtons: function () { },

    // -------------------------------------------------------------------------
    // Private
    // -------------------------------------------------------------------------
    /**
     * Add Switcher View Mobile / Desktop near pager
     *
     * @private
     */
    _updateControlPanelProps: async function () {
        const props = this._super(...arguments);
        const $switchModeButton = $(qweb.render('website.ThemePreview.SwitchModeButton'));
        this.controlPanelProps.cp_content.$pager = $switchModeButton;
        return props;
    },

    // -------------------------------------------------------------------------
    // Handlers
    // -------------------------------------------------------------------------
    /**
     * Handler called when user click on 'Desktop/Mobile' switcher button.
     *
     * @private
     */
    _onSwitchButtonChange: function () {
        this.$('.o_preview_frame').toggleClass('is_mobile');
    },
    /**
     * Handler called when user click on 'Choose another theme' button.
     *
     * @private
     */
    _onSwitchThemeClick: function () {
        this.trigger_up('history_back');
    },
    /**
     * Handler called when user click on 'START NOW' button in form view.
     *
     * @private
     */
    _onStartNowClick: function () {
        this._handleThemeAction(this.getSelectedIds()[0], 'button_choose_theme');
    },
});

var ThemePreviewFormView = FormView.extend({
    config: _.extend({}, FormView.prototype.config, {
        Controller: ThemePreviewController
    }),
});

viewRegistry.add('theme_preview_form', ThemePreviewFormView);

return {
    ThemePreviewControllerCommon: ThemePreviewControllerCommon
}
});
