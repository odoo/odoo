odoo.define('web.CalendarController', function (require) {
"use strict";

/**
 * Calendar Controller
 *
 * This is the controller in the Model-Renderer-Controller architecture of the
 * calendar view.  Its role is to coordinate the data from the calendar model
 * with the renderer, and with the outside world (such as a search view input)
 */

var AbstractController = require('web.AbstractController');
var QuickCreate = require('web.CalendarQuickCreate');
var dialogs = require('web.view_dialogs');
var Dialog = require('web.Dialog');
var core = require('web.core');

var _t = core._t;
var QWeb = core.qweb;

var CalendarController = AbstractController.extend({
    custom_events: _.extend({}, AbstractController.prototype.custom_events, {
        quickCreate: '_onQuickCreate',
        openCreate: '_onOpenCreate',
        openEvent: '_onOpenEvent',
        dropRecord: '_onDropRecord',
        updateRecord: '_onUpdateRecord',
        changeDate: '_onChangeDate',
        changeFilter: '_onChangeFilter',
        toggleFullWidth: '_onToggleFullWidth',
    }),
    /**
     * @override
     * @param {Widget} parent
     * @param {AbstractModel} model
     * @param {AbstractRenderer} renderer
     * @param {Object} params
     */
    init: function (parent, model, renderer, params) {
        this._super.apply(this, arguments);
        this.current_start = null;
        this.quickAddPop = params.quickAddPop;
        this.disableQuickCreate = params.disableQuickCreate;
        this.eventOpenPopup = params.eventOpenPopup;
        this.formViewId = params.formViewId;
        this.readonlyFormViewId = params.readonlyFormViewId;
        this.mapping = params.mapping;
        this.context = params.context;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------


    /**
     * Render the buttons according to the CalendarView.buttons template and
     * add listeners on it. Set this.$buttons with the produced jQuery element
     *
     * @param {jQueryElement} [$node] a jQuery node where the rendered buttons
     *   should be inserted. $node may be undefined, in which case the Calendar
     *   inserts them into this.options.$buttons or into a div of its template
     */
    renderButtons: function ($node) {
        var self = this;
        this.$buttons = $(QWeb.render("CalendarView.buttons", {'widget': this}));
        this.$buttons.on('click', 'button.o_calendar_button_new', function () {
            self.trigger_up('switch_view', {view_type: 'form'});
        });

        _.each(['prev', 'today', 'next'], function (action) {
            self.$buttons.on('click', '.o_calendar_button_' + action, function () {
                self.model[action]();
                self.reload();
            });
        });
        _.each(['day', 'week', 'month'], function (scale) {
            self.$buttons.on('click', '.o_calendar_button_' + scale, function () {
                self.model.setScale(scale);
                self.reload();
            });
        });

        this.$buttons.find('.o_calendar_button_' + this.mode).addClass('active');

        if ($node) {
            this.$buttons.appendTo($node);
        } else {
            this.$('.o_calendar_buttons').replaceWith(this.$buttons);
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @param {Object} record
     * @param {integer} record.id
     * @returns {Deferred}
     */
    _updateRecord: function (record) {
        return this.model.updateRecord(record).then(this.reload.bind(this));
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @param {OdooEvent} event
     */
    _onChangeDate: function (event) {
        var modelData = this.model.get();
        if (modelData.target_date.toString() === event.data.date) {
            switch (modelData.scale) {
                case 'month': this.model.setScale('week'); break;
                case 'week': this.model.setScale('day'); break;
                case 'day': this.model.setScale('month'); break;
            }
        } else {
            this.model.setScale('week');
        }
        this.model.setDate(event.data.date, true);
        this.reload();
    },
    /**
     * @param {OdooEvent} event
     */
    _onChangeFilter: function (event) {
        if (this.model.changeFilter(event.data) && !event.data.no_reload) {
            this.reload();
        }
    },
    /**
     * @param {OdooEvent} event
     */
    _onDropRecord: function (event) {
        this._updateRecord(event.data);
    },
    /**
     * Handles saving data coming from quick create box
     *
     * @private
     * @param {OdooEvent} event
     */
    _onQuickCreate: function (event) {
        var self = this;
        this.model.createRecord(event)
            .then(function (id) {
                self.quick.destroy();
                self.quick = null;
                self.reload(id);
            }, function () {
                // This will occurs if there are some more fields required
                event.data.options.disableQuickCreate = true;
                event.data.data.on_save = self.quick.destroy.bind(self.quick);
                self._onOpenCreate(event.data);
            });
    },
    /**
     * @param {OdooEvent} event
     */
    _onOpenCreate: function (event) {
        var self = this;
        if (this.model.get().scale === "month") {
            event.data.allDay = true;
        }
        var data = this.model.calendarEventToRecord(event.data);

        var context = _.extend({}, this.context, event.options && event.options.context);
        context.default_name = data.name || null;
        context['default_' + this.mapping.date_start] = data.start || null;
        if (this.mapping.date_stop) {
            context['default_' + this.mapping.date_stop] = data.stop || null;
        }
        if (this.mapping.date_delay) {
            context['default_' + this.mapping.date_delay] = data.duration || null;
        }
        if (this.mapping.all_day) {
            context['default_' + this.mapping.all_day] = data[this.mapping.all_day] || null;
        }

        for (var k in context) {
            if (context[k] && context[k]._isAMomentObject) {
                context[k] = context[k].clone().utc().format('YYYY-MM-DD HH:mm:ss');
            }
        }

        var options = _.extend({}, this.options, event.options, {context: context});

        if (this.quick != null) {
            this.quick.destroy();
            this.quick = null;
        }

        if(!options.disableQuickCreate && !event.data.disableQuickCreate && this.quickAddPop) {
            this.quick = new QuickCreate(this, true, options, data, event.data);
            this.quick.on('added', this, this.reload.bind(this));
            this.quick.open();
            this.quick.focus();
            return;
        }

        var title = _t("Create");
        if (this.renderer.arch.attrs.string) {
            title += ': ' + this.renderer.arch.attrs.string;
        }
        if (this.eventOpenPopup) {
            new dialogs.FormViewDialog(self, {
                res_model: this.modelName,
                context: context,
                title: title,
                disable_multiple_selection: true,
                on_saved: function () {
                    if (event.data.on_save) {
                        event.data.on_save();
                    }
                    self.reload();
                },
            }).open();
        } else {
            this.do_action({
                type: 'ir.actions.act_window',
                res_model: this.modelName,
                views: [[this.formViewId || false, 'form']],
                target: 'current',
                context: context,
            });
        }
    },
    /**
     * @param {OdooEvent} event
     */
    _onOpenEvent: function (event) {
        var self = this;
        var id = event.data._id;
        id = id && parseInt(id).toString() === id ? parseInt(id) : id;

        if (!this.eventOpenPopup) {
            this.do_action({
                type: 'ir.actions.act_window',
                res_id: id,
                res_model: this.modelName,
                views: [[this.formViewId || false, 'form']],
                target: 'current',
                context: event.context || self.context,
            });
            return;
        }

        var open_dialog = function (readonly) {
            var options = {
                res_model: self.modelName,
                res_id: id || null,
                context: event.context || self.context,
                readonly: readonly,
                title: _t("Open: ") + event.data.title,
                on_saved: function () {
                    if (event.data.on_save) {
                        event.data.on_save();
                    }
                    self.reload();
                },
            };
            if (readonly) {
                if (self.readonlyFormViewId) {
                    options.view_id = parseInt(self.readonlyFormViewId);
                }
                options.buttons = [
                    {
                        text: _t("Edit"),
                        classes: 'btn-primary',
                        close: true,
                        click: function () { open_dialog(false); }
                    },
                    {
                        text: _t("Delete"),
                        click: function () {
                            Dialog.confirm(this, _t("Are you sure you want to delete this record ?"), {
                                confirm_callback: function () {
                                    self.model.deleteRecords([id], self.modelName)
                                        .then(function () {
                                            self.dialog.destroy();
                                            self.reload();
                                        });
                                }
                            });
                        },
                    },
                    {text: _t("Close"), close: true}
                ];
            } else if (self.formViewId) {
                options.view_id = parseInt(self.formViewId);
            }
            self.dialog = new dialogs.FormViewDialog(self, options).open();
        };
        open_dialog(true);
    },
    /**
     * Called when we want to open or close the sidebar.
     */
    _onToggleFullWidth: function () {
        this.model.toggleFullWidth();
        this.reload();
    },
    /**
     * @param {OdooEvent} event
     */
    _onUpdateRecord: function (event) {
        this._updateRecord(event.data);
    },
});

return CalendarController;

});
