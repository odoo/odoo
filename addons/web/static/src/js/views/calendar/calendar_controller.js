odoo.define('web.CalendarController', function (require) {
    "use strict";

    /**
     * Calendar Controller
     *
     * This is the controller in the Model-Renderer-Controller architecture of the
     * calendar view.  Its role is to coordinate the data from the calendar model
     * with the renderer, and with the outside world (such as a search view input)
     */

    const AbstractController = require('web.AbstractController');
    const config = require('web.config');
    const core = require('web.core');
    const Dialog = require('web.Dialog');
    const dialogs = require('web.view_dialogs');
    const QuickCreate = require('web.CalendarQuickCreate');

    const _t = core._t;
    const QWeb = core.qweb;

    function dateToServer(date) {
        return date.clone().utc().locale('en').format('YYYY-MM-DD HH:mm:ss');
    }

    const CalendarController = AbstractController.extend({
        custom_events: Object.assign({}, AbstractController.prototype.custom_events, {
            changeDate: '_onChangeDate',
            changeFilter: '_onChangeFilter',
            deleteRecord: '_onDeleteRecord',
            dropRecord: '_onDropRecord',
            next: '_onNext',
            openEvent: '_onOpenEvent',
            openCreate: '_onOpenCreate',
            prev: '_onPrev',
            quickCreate: '_onQuickCreate',
            updateRecord: '_onUpdateRecord',
            viewUpdated: '_onViewUpdated',
        }),
        /**
         * @override
         * @param {Widget} parent
         * @param {AbstractModel} model
         * @param {AbstractRenderer} renderer
         * @param {Object} params
         */
        init(parent, model, renderer, params) {
            this._super(...arguments);
            this.current_start = null;
            this.displayName = params.displayName;
            this.quickAddPop = params.quickAddPop;
            this.disableQuickCreate = params.disableQuickCreate;
            this.eventOpenPopup = params.eventOpenPopup;
            this.showUnusualDays = params.showUnusualDays;
            this.formViewId = params.formViewId;
            this.readonlyFormViewId = params.readonlyFormViewId;
            this.mapping = params.mapping;
            this.context = params.context;
            this.previousOpen = null;
            // The quickCreating attribute ensures that we don't do several create
            this.quickCreating = false;
        },
        /**
         * Overrides to unbind handler on the control panel mobile 'Today' button.
         *
         * @override
         */
        destroy() {
            this._super(...arguments);
            if (this.$todayButton) {
                this.$todayButton.off();
            }
        },

        //--------------------------------------------------------------------------
        // Public
        //--------------------------------------------------------------------------

        /**
         * @override
         * @returns {string}
         */
        getTitle() {
            return this._title;
        },
        /**
         * Render the buttons according to the CalendarView.buttons template and
         * add listeners on it. Set this.$buttons with the produced jQuery element
         *
         * @param {jQueryElement} [$node] a jQuery node where the rendered buttons
         *   should be inserted. $node may be undefined, in which case the Calendar
         *   inserts them into this.options.$buttons or into a div of its template
         */
        renderButtons($node) {
            this.$buttons = $(QWeb.render('CalendarView.buttons', {
                isMobile: config.device.isMobile,
            }));
            this.$buttons.on('click', 'button.o_calendar_button_new', () => {
                this.trigger_up('switch_view', {view_type: 'form'});
            });

            ['prev', 'today', 'next'].forEach(action => {
                this.$buttons.on('click', '.o_calendar_button_' + action, () => {
                    this._move(action);
                });
            });
            ['day', 'week', 'month'].forEach(scale => {
                this.$buttons.on('click', '.o_calendar_button_' + scale, () => {
                    this.model.setScale(scale);
                    this.reload();
                });
            });

            this.$buttons.find('.o_calendar_button_' + this.mode).addClass('active');

            if ($node) {
                this.$buttons.appendTo($node);
            } else {
                this.$('.o_calendar_buttons').replaceWith(this.$buttons);
            }
        },
        /**
         * In mobile, we want to display a special 'Today' button on the bottom
         * right corner of the control panel. This is the pager area, and as there
         * is no pager in Calendar views, we fool the system by defining a fake
         * pager (which is actually our button) such that it will be inserted in the
         * desired place.
         *
         * @todo get rid of this hack once the ControlPanel layout will be reworked
         *
         * @param {jQueryElement} $node the button should be appended to this
         *   element to be displayed in the bottom right corner of the control panel
         */
        renderPager($node) {
            if (config.device.isMobile) {
                this.$todayButton = $(QWeb.render('CalendarView.TodayButtonMobile'));
                this.$todayButton.on('click', this._move.bind(this, 'today'));
                $node.append(this.$todayButton);
            }
        },

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * Move to the requested direction and reload the view
         *
         * @private
         * @param {string} to either 'prev', 'next' or 'today'
         * @returns {Promise}
         */
        _move(to) {
            this.model[to]();
            return this.reload();
        },
        /**
         * @override
         * @private
         */
        async _update() {
            if (!this.showUnusualDays) {
                return await this._super(...arguments);
            }
            const result = await this._super(...arguments);
            const data = await this._rpc({
                model: this.modelName,
                method: 'get_unusual_days',
                args: [this.model.data.start_date.format('YYYY-MM-DD'), this.model.data.end_date.format('YYYY-MM-DD')],
                context: this.context,
            });
            this.el.querySelectorAll('td.fc-day').forEach(td => {
                if (data[td.getAttribute('data-date')]) {
                    td.classList.add('o_calendar_disabled');
                }
            });
            return result;
        },
        /**
         * @private
         * @param {Object} record
         * @param {integer} record.id
         * @returns {Promise}
         */
        _updateRecord(record) {
            const reload = this.reload.bind(this, {});
            return this.model.updateRecord(record).then(reload, reload);
        },

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        /**
         * @private
         * @param {CustomEvent} event
         */
        _onChangeDate(event) {
            const modelData = this.model.get();
            if (modelData.target_date.format('YYYY-MM-DD') === event.data.date.format('YYYY-MM-DD')) {
                // When clicking on same date, toggle between the two views
                switch (modelData.scale) {
                    case 'month': this.model.setScale('week'); break;
                    case 'week': this.model.setScale('day'); break;
                    case 'day': this.model.setScale('month'); break;
                }
            } else if (modelData.target_date.week() === event.data.date.week()) {
                // When clicking on a date in the same week, switch to day view
                this.model.setScale('day');
            } else {
                // When clicking on a random day of a random other week, switch to week view
                this.model.setScale('week');
            }
            this.model.setDate(event.data.date);
            this.reload();
        },
        /**
         * @private
         * @param {CustomEvent} event
         */
        _onChangeFilter(event) {
            if (this.model.changeFilter(event.data) && !event.data.no_reload) {
                this.reload();
            }
        },
        /**
         * @private
         * @param {CustomEvent} event
         */
        _onDeleteRecord(event) {
            Dialog.confirm(this, _t("Are you sure you want to delete this record ?"), {
                confirm_callback: () => {
                    this.model.deleteRecords([event.data.id], this.modelName).then(() => {
                        this.reload();
                    });
                }
            });
        },
        /**
         * @private
         * @param {CustomEvent} event
         */
        _onDropRecord(event) {
            this._updateRecord(Object.assign({}, event.data, {
                'drop': true,
            }));
        },
        /**
         * @private
         * @param {CustomEvent} event
         */
        _onNext(event) {
            event.stopPropagation();
            this._move('next');
        },
        /**
         * @private
         * @param {CustomEvent} event
         */
        _onOpenCreate(event) {
            const eventData = event.data || event.detail || {};
            if (this.model.get().scale === "month") {
                eventData.allDay = true;
            }
            const data = this.model.calendarEventToRecord(eventData);

            const context = Object.assign({}, this.context, event.options && event.options.context);
            // context default has more priority in default_get so if data.name is false then it may
            // lead to error/warning while saving record in form view as name field can be required
            if (data.name) {
                context.default_name = data.name;
            }
            context['default_' + this.mapping.date_start] = data[this.mapping.date_start] || null;
            if (this.mapping.date_stop) {
                context['default_' + this.mapping.date_stop] = data[this.mapping.date_stop] || null;
            }
            if (this.mapping.date_delay) {
                context['default_' + this.mapping.date_delay] = data[this.mapping.date_delay] || null;
            }
            if (this.mapping.all_day) {
                context['default_' + this.mapping.all_day] = data[this.mapping.all_day] || null;
            }

            for (const k in context) {
                if (context[k] && context[k]._isAMomentObject) {
                    context[k] = dateToServer(context[k]);
                }
            }

            const options = Object.assign({}, this.options, event.options, {
                context: context,
                title: _t(`Create: ${this.displayName || this.renderer.props.arch.attrs.string}`)
            });

            if (this.quick != null) {
                this.quick.destroy();
                this.quick = null;
            }

            if (!options.disableQuickCreate && !eventData.disableQuickCreate && this.quickAddPop) {
                this.quick = new QuickCreate(this, true, options, data, eventData);
                this.quick.open();
                this.quick.opened(() => {
                    this.quick.focus();
                });
                return;
            }

            let title = _t("Create");
            if (this.renderer.props.arch.attrs.string) {
                title += ': ' + this.renderer.props.arch.attrs.string;
            }
            if (this.eventOpenPopup) {
                if (this.previousOpen) { this.previousOpen.close(); }
                this.previousOpen = new dialogs.FormViewDialog(this, {
                    res_model: this.modelName,
                    context: context,
                    title: title,
                    view_id: this.formViewId || false,
                    disable_multiple_selection: true,
                    on_saved: () => {
                        if (event.data.on_save) {
                            event.data.on_save();
                        }
                        this.reload();
                    },
                });
                this.previousOpen.open();
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
         * @private
         * @param {CustomEvent} event
         */
        async _onOpenEvent(event) {
            let id = event.data._id;
            id = id && parseInt(id).toString() === id ? parseInt(id) : id;

            if (!this.eventOpenPopup) {
                const viewId = await this._rpc({
                    model: this.modelName,
                    method: 'get_formview_id',
                    //The event can be called by a view that can have another context than the default one.
                    args: [[id]],
                    context: event.context || this.context,
                });
                this.do_action({
                    type: 'ir.actions.act_window',
                    res_id: id,
                    res_model: this.modelName,
                    views: [[viewId || false, 'form']],
                    target: 'current',
                    context: event.context || this.context,
                });
                return;
            }

            const options = {
                res_model: this.modelName,
                res_id: id || null,
                context: event.context || this.context,
                title: _t("Open: ") + event.data.title,
                on_saved: () => {
                    if (event.data.on_save) {
                        event.data.on_save();
                    }
                    this.reload();
                },
            };
            if (this.formViewId) {
                options.view_id = parseInt(this.formViewId);
            }
            new dialogs.FormViewDialog(this, options).open();
        },
        /**
         * @private
         * @param {CustomEvent} event
         */
        _onPrev(event) {
            event.stopPropagation();
            this._move('prev');
        },

        /**
         * Handles saving data coming from quick create box
         *
         * @private
         * @param {CustomEvent} event
         */
        _onQuickCreate(event) {
            const self = this;
            if (this.quickCreating) {
                return;
            }
            this.quickCreating = true;
            this.model.createRecord(event)
                .then(function () {
                    self.quick.destroy();
                    self.quick = null;
                    self.reload();
                    self.quickCreating = false;
                })
                .guardedCatch(function (result) {
                    var errorEvent = result.event;
                    // This will occurs if there are some more fields required
                    // Preventdefaulting the error event will prevent the traceback window
                    errorEvent.preventDefault();
                    event.data.options.disableQuickCreate = true;
                    event.data.on_save = self.quick.destroy.bind(self.quick);
                    self._onOpenCreate(event.data);
                    self.quickCreating = false;
                });
        },
        /**
         * @private
         * @param {CustomEvent} event
         */
        _onUpdateRecord(event) {
            this._updateRecord(event.data);
        },
        /**
         * The internal state of the calendar (mode, period displayed) has changed,
         * so update the control panel buttons and breadcrumbs accordingly.
         *
         * @private
         * @param {CustomEvent} event
         */
        _onViewUpdated(event) {
            this.mode = event.data.mode;
            if (this.$buttons) {
                this.$buttons.find('.active').removeClass('active');
                this.$buttons.find('.o_calendar_button_' + this.mode).addClass('active');
            }
            this._setTitle(this.displayName + ' (' + event.data.title + ')');
        },
    });

    return CalendarController;

});
