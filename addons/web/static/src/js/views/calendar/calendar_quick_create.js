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
     * @param {string} modelName
     * @param {any} buttons
     * @param {any} options
     * @param {any} data_template
     * @param {any} data_calendar
     */
    init: function (parent, modelName, buttons, options, data_template, data_calendar) {
        this.modelName = modelName;
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
                    if (!self._quickAdd()) {
                        self.focus();
                    }
                }},
                {text: _t("Edit"), click: function () {
                    data_calendar.disable_quick_create = true;
                    data_calendar.title = self.$input.val().trim();
                    data_calendar.on_save = self.destroy.bind(self);
                    self.trigger_up('openCreate', data_calendar);
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
        this.on('added', this, function () {
            self.close();
        });

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
    _quickAdd: function () {
        var val = this.$input.val().trim();
        return (val)? this._quickCreate({'name': val}, this.options) : false;
    },
    /**
     * Handles saving data coming from quick create box
     */
    _quickCreate: function (data, options) {
        var self = this;
        return this._rpc(this.modelName, 'create')
            .args([$.extend({}, this.data_template, data)])
            .withContext(_.pick(options, 'context'))
            .exec()
            .then(function (id) {
                self.trigger('added', id);
                self.$input.val("");
            }, function (r, event) {
                event.preventDefault();
                // This will occurs if there are some more fields required
                self.slow_create(data);
            });
    },
});

return QuickCreate;

});
