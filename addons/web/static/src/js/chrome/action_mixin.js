odoo.define('web.ActionMixin', function (require) {
"use strict";

/**
 * We define here the ActionMixin, the generic notion of action (from the point
 * of view of the web client).  In short, an action is a widget which controls
 * the main part of the screen (everything below the navbar).
 *
 * More precisely, the action manager is the component that coordinates a stack
 * of actions.  Whenever the user navigates in the interface, switches views,
 * open different menus, the action manager creates/updates/destroys special
 * widgets which implements the ActionMixin.  These actions need to answer to a
 * standardised API, which is the reason for this mixin.
 *
 * In practice, most actions are view controllers (coming from an
 * ir.action.act_window).  However, some actions are 'client actions'.  They
 * also need to implement the ActionMixin for a better cooperation with the
 * action manager.
 *
 * @module web.ActionMixin
 */

var core = require('web.core');

var ActionMixin = {
    template: 'Action',

    /**
     * The action mixin assumes that it is rendered with the 'Action' template.
     * This template has a special zone ('.o_content') where the content should
     * be added.  Actions that want to automatically render a template there
     * should define the contentTemplate key.  In short, client actions should
     * probably define a contentTemplate key, and not a template key.
     */
    contentTemplate: null,

    /**
     * Events built by and managed by Odoo Framework
     *
     * It is expected that any Widget Class implementing this mixin
     * will also implement the ParentedMixin which actually manages those
     */
    custom_events: {
        get_controller_query_params: '_onGetControllerQueryParams',
    },
    /**
     * If an action wants to use a control panel, it will be created and
     * registered in this _controlPanel key (the widget).  The way this control
     * panel is created is up to the implementation (so, view controllers or
     * client actions may have different needs).
     *
     * Note that most of the time, this key should be set by the framework, not
     * by the code of the client action.
     */
    _controlPanel: null,

    /**
     * String containing the title of the client action (which may be needed to
     * display in the breadcrumbs zone of the control panel).
     *
     * @see _setTitle
     */
    _title: '',

    /**
     * @override
     */
    renderElement: function () {
        this._super.apply(this, arguments);
        if (this.contentTemplate) {
            var content = core.qweb.render(this.contentTemplate, {widget: this});
            this.$('.o_content').append(content);
        }
    },
    /**
     * Called each time the action is attached into the DOM.
     */
    on_attach_callback: function () {},
    /**
     * Called each time the action is detached from the DOM.
     */
    on_detach_callback: function () {},
    /**
     * Called by the action manager when action is restored (typically, when the
     * user clicks on the action in the breadcrumb)
     *
     * @returns {Promise|undefined}
     */
    willRestore: function () {},

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * In some situations, we need confirmation from the controller that the
     * current state can be destroyed without prejudice to the user.  For
     * example, if the user has edited a form, maybe we should ask him if we
     * can discard all his changes when we switch to another action.  In that
     * case, the action manager will call this method.  If the returned
     * promise is successfully resolved, then we can destroy the current action,
     * otherwise, we need to stop.
     *
     * @returns {Promise} resolved if the action can be removed, rejected
     *   otherwise
     */
    canBeRemoved: function () {
        return Promise.resolve();
    },
    /**
     * This function is called when the current state of the action
     * should be known. For instance, if the action is a view controller,
     * this may be useful to reinstantiate a view in the same state.
     *
     * Typically the state can (and should) be encoded in a query object of
     * the form::
     *
     *     {
     *          context: {...},
     *          groupBy: [...],
     *          domain = [...],
     *          orderedBy = [...],
     *     }
     *
     * where the context key can contain many information.
     * This method is mainly called during the creation of a custom filter.
     *
     * @returns {Object}
     */
    getOwnedQueryParams: function () {
        return {};
    },
    /**
     * Returns a title that may be displayed in the breadcrumb area.  For
     * example, the name of the record (for a form view). This is actually
     * important for the action manager: this is the way it is able to give
     * the proper titles for other actions.
     *
     * @returns {string}
     */
    getTitle: function () {
        return this._title;
    },
    /**
     * Gives the focus to the action
     */
    giveFocus: function () {
    },
    /**
     * Renders the buttons to append, in most cases, to the control panel (in
     * the bottom left corner). When the action is rendered in a dialog, those
     * buttons might be moved to the dialog's footer.
     *
     * @param {jQuery Node} $node
     */
    renderButtons: function ($node) {
    },
    /**
     * This is the main method to customize the controlpanel content.
     *
     * @see updateContents method in ControlPanelRenderer for more info
     *
     * @param {Object} [status]
     * @param {string} [status.title]
     * @param {Object} [options]
     * @param {boolean} [options.clear]
     */
    updateControlPanel: function (status, options) {
        if (this._controlPanel) {
            status = status || {};
            status.title = status.title || this.getTitle();
            this._controlPanel.updateContents(status, options || {});
        }
    },
    // TODO: add hooks methods:
    // - onRestoreHook (on_reverse_breadcrumbs)

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {string} title
     */
    _setTitle: function (title) {
        this._title = title;
        this.updateControlPanel({title: this._title}, {clear: false});
    },
    /**
     * FIXME: this logic should be rethought
     *
     * Handles a context request: provides to the caller the state of the
     * current controller.
     *
     * @private
     * @param {OdooEvent} ev
     * @param {function} ev.data.callback used to send the requested state
     */
    _onGetControllerQueryParams: function (ev) {
        ev.stopPropagation();
        var state = this.getOwnedQueryParams();
        ev.data.callback(state || {});
    },
};

return ActionMixin;

});
