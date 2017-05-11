odoo.define('web.ViewWidget', function (require) {
"use strict";

/**
* This is the basic widget used by all other widgets.
* 
* The responsabilities of a field widget are mainly:
* - activate widget when focus comes on widget
* - keydown and keyup handler for navigation on widgets
*
* @module web.ViewWidget
*/

var ajax = require('web.ajax');
var Widget = require('web.Widget');

var ViewWidget = Widget.extend({
    cssLibs: [],
    jsLibs: [],
    events: {
        'keydown': '_onKeydown',
        'keyup': '_onKeyup'
    },
    custom_events: {
        navigation_move: '_onNavigationMove',
    },

    /**
    * An object representing fields to be fetched by the model eventhough not present in the view
    * This object contains "field name" as key and an object as value.
    * That value object must contain the key "type"
    * see FieldBinaryImage for an example.
    */
    fieldDependencies: {},

    /**
     * Loads the libraries listed in this.jsLibs and this.cssLibs
     *
     * @override
     */
    willStart: function () {
        return $.when(ajax.loadLibs(this), this._super.apply(this, arguments));
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Activates the field widget. By default, activation means focusing and
     * selecting (if possible) the associated focusable element. The selecting
     * part can be disabled.  In that case, note that the focused input/textarea
     * will have the cursor at the very end.
     *
     * @param {Object} [options]
     * @param {boolean} [noselect=false] if false and the input
     *   is of type text or textarea, the content will also be selected
     * @param {Event} [options.event] the event which fired this activation
     * @returns {boolean} true if the widget was activated, false if the
     *                    focusable element was not found or invisible
     */
    activate: function (options) {
        if (this.isFocusable()) {
            var $focusable = this.getFocusableElement();
            $focusable.focus();
            if ($focusable.is('input[type="text"], textarea')) {
                $focusable[0].selectionStart = $focusable[0].selectionEnd = $focusable[0].value.length;
                if (options && !options.noselect) {
                    $focusable.select();
                }
            }
            return true;
        }
        return false;
    },
    /**
     * Returns the main field's DOM element (jQuery form) which can be focused
     * by the browser.
     *
     * @returns {jQuery} main focusable element inside the widget
     */
    getFocusableElement: function () {
        return $();
    },
    /**
     * Returns true iff the widget has a visible element that can take the focus
     *
     * @returns {boolean}
     */
    isFocusable: function () {
        var $focusable = this.getFocusableElement();
        return $focusable.length && $focusable.is(':visible');
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Intercepts navigation keyboard events to prevent their default behavior
     * and notifies the view so that it can handle it its own way.
     *
     * Note: the navigation keyboard events are stopped so that potential parent
     * abstract field does not trigger the navigation_move event a second time.
     * However, this might be controversial, we might wanna let the event
     * continue its propagation and flag it to say that navigation has already
     * been handled (TODO ?).
     *
     * @private
     * @param {KeyEvent} ev
     */
    _onKeydown: function (ev) {
        switch (ev.which) {
            case $.ui.keyCode.TAB:
                ev.preventDefault();
                ev.stopPropagation();
                this.trigger_up('navigation_move', {
                    direction: ev.shiftKey ? 'previous' : 'next',
                });
                break;
            case $.ui.keyCode.ENTER:
                ev.stopPropagation();
                this.trigger_up('navigation_move', {direction: 'next_line'});
                break;
            case $.ui.keyCode.ESCAPE:
                this.trigger_up('navigation_move', {direction: 'cancel', originalEvent: ev});
                break;
            case $.ui.keyCode.UP:
                ev.stopPropagation();
                this.trigger_up('navigation_move', {direction: 'up'});
                break;
            case $.ui.keyCode.RIGHT:
                ev.stopPropagation();
                this.trigger_up('navigation_move', {direction: 'right'});
                break;
            case $.ui.keyCode.DOWN:
                ev.stopPropagation();
                this.trigger_up('navigation_move', {direction: 'down'});
                break;
            case $.ui.keyCode.LEFT:
                ev.stopPropagation();
                this.trigger_up('navigation_move', {direction: 'left'});
                break;
        }
    },
    /**
     * Updates the target data value with the current AbstractField instance.
     * This allows to consider the parent field in case of nested fields. The
     * field which triggered the event is still accessible through ev.target.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onNavigationMove: function (ev) {
        ev.data.target = this;
    },
    _onKeyup: function(event) {
        if (event.which === $.ui.keyCode.ESCAPE) {
            this._onKeyupEscape();
        }
    },
    _onKeyupEscape: function() {}
});

return ViewWidget;

});