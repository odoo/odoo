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
    /**
     * @constructor
     * @param {Widget} parent
     * @param {Object} buttons
     * @param {Object} options
     * @param {Object} data_template
     * @param {Object} dataCalendar
     */
    init: function (parent, buttons, options, data_template, dataCalendar) {
        this._buttons = buttons || false;
        this.options = options;

        // Can hold data pre-set from where you clicked on agenda
        this.data_template = data_template || {};
        this.$input = $();

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
                    dataCalendar.disable_quick_create = true;
                    dataCalendar.title = self.$input.val().trim();
                    dataCalendar.on_save = self.destroy.bind(self);
                    self.trigger_up('openCreate', dataCalendar);
                }},
                {text: _t("Cancel"), close: true},
            ] : [],
            $content: QWeb.render('CalendarView.quick_create', {widged: this})
        });
    },
    /**
     * @override
     * @returns {Deferred}
     */
    start: function () {
        var self = this;

        if (this.options.disable_quick_create) {
            this.slow_create();
            return;
        }
        this.$input = this.$('input').keyup(function enterHandler (e) {
            if(e.keyCode === $.ui.keyCode.ENTER) {
                self.$input.off('keyup', enterHandler);
                if (!self._quickAdd()){
                    self.$input.on('keyup', enterHandler);
                }
            } else if (e.keyCode === $.ui.keyCode.ESCAPE && self._buttons) {
                self.close();
            }
        });

        return this._super();
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    focus: function () {
        this.$input.focus();
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
        var val = this.$input.val().trim();
        dataCalendar.title = val;
        return (val)? this.trigger_up('quickCreate', {data: dataCalendar, options: this.options}) : false;
    },
});

return QuickCreate;

});
