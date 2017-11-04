odoo.define('web.CalendarQuickCreate', function (require) {
"use strict";

var core = require('web.core');
var Dialog = require('web.Dialog');

var _t = core._t;
var QWeb = core.qweb;

/**
 * Quick creation view.
 *
 * Triggers a single event "added" with a single parameter "name", which is the
 * name entered by the user
 *
 * @class
 * @type {*}
 */
var QuickCreate = Dialog.extend({
    events: _.extend({}, Dialog.events, {
        'keyup input': '_onkeyup',
    }),

    /**
     * @constructor
     * @param {Widget} parent
     * @param {Object} buttons
     * @param {Object} options
     * @param {Object} dataTemplate
     * @param {Object} dataCalendar
     */
    init: function (parent, buttons, options, dataTemplate, dataCalendar) {
        this._buttons = buttons || false;
        this.options = options;

        // Can hold data pre-set from where you clicked on agenda
        this.dataTemplate = dataTemplate || {};
        this.dataCalendar = dataCalendar;

        var self = this;
        this._super(parent, {
            title: this._getTitle(),
            size: 'small',
            buttons: this._buttons ? [
                {text: _t("Create"), classes: 'btn-primary', click: function () {
                    if (!self._quickAdd(dataCalendar)) {
                        self.focus();
                    }
                }},
                {text: _t("Edit"), click: function () {
                    dataCalendar.disableQuickCreate = true;
                    dataCalendar.title = self.$('input').val().trim();
                    dataCalendar.on_save = self.destroy.bind(self);
                    self.trigger_up('openCreate', dataCalendar);
                }},
                {text: _t("Cancel"), close: true},
            ] : [],
            $content: QWeb.render('CalendarView.quick_create', {widget: this})
        });
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    focus: function () {
        this.$('input').focus();
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {string}
     */
    _getTitle: function () {
        var parent = this.getParent();
        if (_.isUndefined(parent)) {
            return _t("Create");
        }
        var title = (_.isUndefined(parent.field_widget)) ?
                (parent.title || parent.string || parent.name) :
                (parent.field_widget.string || parent.field_widget.name || '');
        return _t("Create: ") + title;
    },
    /**
     * Gathers data from the quick create dialog a launch quick_create(data) method
     */
    _quickAdd: function (dataCalendar) {
        dataCalendar = $.extend({}, this.dataTemplate, dataCalendar);
        var val = this.$('input').val().trim();
        dataCalendar.title = val;
        return (val)? this.trigger_up('quickCreate', {data: dataCalendar, options: this.options}) : false;
    },
    /**
     * @private
     * @param {keyEvent} event
     */
    _onkeyup: function (event) {
        if (this._flagEnter) {
            return;
        }
        if(event.keyCode === $.ui.keyCode.ENTER) {
            this._flagEnter = true;
            if (!this._quickAdd(this.dataCalendar)){
                this._flagEnter = false;
            }
        } else if (event.keyCode === $.ui.keyCode.ESCAPE && this._buttons) {
            this.close();
        }
    },
});

return QuickCreate;

});
