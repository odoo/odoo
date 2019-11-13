odoo.define('web.CalendarQuickCreate', function (require) {
    "use strict";

    const core = require('web.core');
    const Dialog = require('web.Dialog');

    const _t = core._t;
    const QWeb = core.qweb;

    /**
     * Quick creation view.
     *
     * Triggers a single event "added" with a single parameter "name", which is the
     * name entered by the user
     *
     * @class
     * @type {*}
     */
    const QuickCreate = Dialog.extend({
        events: Object.assign({}, Dialog.events, {
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
        init(parent, buttons, options, dataTemplate, dataCalendar) {
            this._buttons = buttons || false;
            this.options = options;

            // Can hold data pre-set from where you clicked on agenda
            this.dataTemplate = dataTemplate || {};
            this.dataCalendar = dataCalendar;

            const self = this;
            this._super(parent, {
                title: options.title,
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

        focus() {
            this.$('input').focus();
        },

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * Gathers data from the quick create dialog a launch quick_create(data) method
         */
        _quickAdd(dataCalendar) {
            dataCalendar = $.extend({}, this.dataTemplate, dataCalendar);
            const val = this.$('input').val().trim();
            if (!val) {
                this.$('label, input').addClass('o_field_invalid');
                const warnings = `<ul><li>${_t("Summary")}</li></ul>`;
                this.do_warn(_t("The following field is invalid:"), warnings);
            }
            dataCalendar.title = val;
            if (val) {
                this.trigger_up('quickCreate', {data: dataCalendar, options: this.options});
            } else {
                return false;
            }
            // return (val)? this.trigger_up('quickCreate', {data: dataCalendar, options: this.options}) : false;
        },

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        /**
         * @private
         * @param {keyEvent} event
         */
        _onkeyup(event) {
            if (this._flagEnter) {
                return;
            }
            if (event.keyCode === 13) {
                this._flagEnter = true;
                if (!this._quickAdd(this.dataCalendar)) {
                    this._flagEnter = false;
                }
            } else if (event.keyCode === 27 && this._buttons) {
                this.close();
            }
        },
    });

    return QuickCreate;
});
