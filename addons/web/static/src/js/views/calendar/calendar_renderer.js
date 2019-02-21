odoo.define('web.CalendarRenderer', function (require) {
"use strict";

var AbstractRenderer = require('web.AbstractRenderer');
var config = require('web.config');
var core = require('web.core');
var Dialog = require('web.Dialog');
var field_utils = require('web.field_utils');
var FieldManagerMixin = require('web.FieldManagerMixin');
var QWeb = require('web.QWeb');
var relational_fields = require('web.relational_fields');
var session = require('web.session');
var utils = require('web.utils');
var Widget = require('web.Widget');

var _t = core._t;
var qweb = core.qweb;

var scales = {
    day: 'agendaDay',
    week: 'agendaWeek',
    month: 'month'
};

var SidebarFilterM2O = relational_fields.FieldMany2One.extend({
    _getSearchBlacklist: function () {
        return this._super.apply(this, arguments).concat(this.filter_ids || []);
    },
});

var SidebarFilter = Widget.extend(FieldManagerMixin, {
    template: 'CalendarView.sidebar.filter',
    custom_events: _.extend({}, FieldManagerMixin.custom_events, {
        field_changed: '_onFieldChanged',
    }),
    /**
     * @constructor
     * @param {Widget} parent
     * @param {Object} options
     * @param {string} options.fieldName
     * @param {Object[]} options.filters A filter is an object with the
     *   following keys: id, value, label, active, avatar_model, color,
     *   can_be_removed
     * @param {Object} [options.favorite] this is an object with the following
     *   keys: fieldName, model, fieldModel
     */
    init: function (parent, options) {
        this._super.apply(this, arguments);
        FieldManagerMixin.init.call(this);

        this.title = options.title;
        this.fields = options.fields;
        this.fieldName = options.fieldName;
        this.write_model = options.write_model;
        this.write_field = options.write_field;
        this.avatar_field = options.avatar_field;
        this.avatar_model = options.avatar_model;
        this.filters = options.filters;
        this.label = options.label;
        this.getColor = options.getColor;
        this.onlyFilter = options.onlyFilter;
    },
    /**
     * @override
     */
    willStart: function () {
        var self = this;
        var defs = [this._super.apply(this, arguments)];

        if (this.write_model || this.write_field) {
            var def = this.model.makeRecord(this.write_model, [{
                name: this.write_field,
                relation: this.fields[this.fieldName].relation,
                type: 'many2one',
            }]).then(function (recordID) {
                self.many2one = new SidebarFilterM2O(self,
                    self.write_field,
                    self.model.get(recordID),
                    {
                        mode: 'edit',
                        attrs: {
                            placeholder: _.str.sprintf(_t("+ Add %s"), self.title),
                            can_create: false
                        },
                    });
            });
            defs.push(def);
        }
        return $.when.apply($, defs);

    },
    /**
     * @override
     */
    start: function () {
        this._super();
        if (this.many2one) {
            this.many2one.appendTo(this.$el);
            this.many2one.filter_ids = _.without(_.pluck(this.filters, 'value'), 'all');
        }
        this.$el.on('click', '.o_remove', this._onFilterRemove.bind(this));
        this.$el.on('click', '.o_calendar_filter_items input', this._onFilterActive.bind(this));
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {OdooEvent} event
     */
    _onFieldChanged: function (event) {
        var self = this;
        event.stopPropagation();
        var createValues = {'user_id': session.uid};
        var value = event.data.changes[this.write_field].id;
        createValues[this.write_field] = value;
        this._rpc({
                model: this.write_model,
                method: 'create',
                args: [createValues],
            })
            .then(function () {
                self.trigger_up('changeFilter', {
                    'fieldName': self.fieldName,
                    'value': value,
                    'active': true,
                });
            });
    },
    /**
     * @private
     * @param {MouseEvent} e
     */
    _onFilterActive: function (e) {
        var $input = $(e.currentTarget);
        this.$el.find('.fc-event').add('.o_calendar_filter_item').popover('dispose');
        this.trigger_up('changeFilter', {
            'fieldName': this.fieldName,
            'value': $input.closest('.o_calendar_filter_item').data('value'),
            'active': $input.prop('checked'),
        });
    },
    /**
     * @private
     * @param {MouseEvent} e
     */
    _onFilterRemove: function (e) {
        var self = this;
        var $filter = $(e.currentTarget).closest('.o_calendar_filter_item');
        Dialog.confirm(this, _t("Do you really want to delete this filter from favorites ?"), {
            confirm_callback: function () {
                self._rpc({
                        model: self.write_model,
                        method: 'unlink',
                        args: [[$filter.data('id')]],
                    })
                    .then(function () {
                        self.trigger_up('changeFilter', {
                            'fieldName': self.fieldName,
                            'id': $filter.data('id'),
                            'active': false,
                            'value': $filter.data('value'),
                        });
                    });
            },
        });
    },
});

return AbstractRenderer.extend({
    template: "CalendarView",

    /**
     * @constructor
     * @param {Widget} parent
     * @param {Object} state
     * @param {Object} params
     */
    init: function (parent, state, params) {
        this._super.apply(this, arguments);
        this.displayFields = params.displayFields;
        this.model = params.model;
        this.filters = [];
        this.color_map = {};

        if (params.eventTemplate) {
            this.qweb = new QWeb(session.debug, {_s: session.origin});
            this.qweb.add_template(utils.json_node_to_xml(params.eventTemplate));
        }
    },
    /**
     * @override
     * @returns {Deferred}
     */
    start: function () {
        this._initSidebar();
        this._initCalendar();
        if (config.device.isMobile) {
            this._bindSwipe();
        }
        return this._super();
    },
    /**
     * @override
     */
    destroy: function () {
        if (this.$calendar) {
            this.$calendar.fullCalendar('destroy');
        }
        if (this.$small_calendar) {
            this.$small_calendar.datepicker('destroy');
            $('#ui-datepicker-div:empty').remove();
        }
        this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Note: this is not dead code, it is called by the calendar-box template
     *
     * @param {any} record
     * @param {any} fieldName
     * @param {any} imageField
     * @returns {string[]}
     */
    getAvatars: function (record, fieldName, imageField) {
        var field = this.state.fields[fieldName];

        if (!record[fieldName]) {
            return [];
        }

        if (field.type === 'one2many' || field.type === 'many2many') {
            return _.map(record[fieldName], function (id) {
                return '<img src="/web/image/'+field.relation+'/'+id+'/'+imageField+'" />';
            });
        } else if (field.type === 'many2one') {
            return ['<img src="/web/image/'+field.relation+'/'+record[fieldName][0]+'/'+imageField+'" />'];
        } else {
            var value = this._format(record, fieldName);
            var color = this.getColor(value);
            if (isNaN(color)) {
                return ['<span class="o_avatar_square" style="background-color:'+color+';"/>'];
            }
            else {
                return ['<span class="o_avatar_square o_calendar_color_'+color+'"/>'];
            }
        }
    },
    /**
     * Note: this is not dead code, it is called by two template
     *
     * @param {any} key
     * @returns {integer}
     */
    getColor: function (key) {
        if (!key) {
            return;
        }
        if (this.color_map[key]) {
            return this.color_map[key];
        }
        // check if the key is a css color
        if (typeof key === 'string' && key.match(/^((#[A-F0-9]{3})|(#[A-F0-9]{6})|((hsl|rgb)a?\(\s*(?:(\s*\d{1,3}%?\s*),?){3}(\s*,[0-9.]{1,4})?\))|)$/i)) {
            return this.color_map[key] = key;
        }
        var index = (((_.keys(this.color_map).length + 1) * 5) % 24) + 1;
        this.color_map[key] = index;
        return index;
    },
    /**
     * @override
     */
    getLocalState: function () {
        var $fcScroller = this.$calendar.find('.fc-scroller');
        return {
            scrollPosition: $fcScroller.scrollTop(),
        };
    },
    /**
     * @override
     */
    setLocalState: function (localState) {
        if (localState.scrollPosition) {
            var $fcScroller = this.$calendar.find('.fc-scroller');
            $fcScroller.scrollTop(localState.scrollPosition);
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * Bind handlers to enable swipe navigation
     *
     * @private
     */
    _bindSwipe: function () {
        var self = this;
        var touchStartX;
        var touchEndX;
        this.$calendar.on('touchstart', function (event) {
            touchStartX = event.originalEvent.touches[0].pageX;
        });
        this.$calendar.on('touchend', function (event) {
            touchEndX = event.originalEvent.changedTouches[0].pageX;
            if (touchStartX - touchEndX > 100) {
                self.trigger_up('next');
            } else if (touchStartX - touchEndX < -100) {
                self.trigger_up('prev');
            }
        });
    },
    /**
     * @param {any} event
     * @returns {string} the html for the rendered event
     */
    _eventRender: function (event) {
        var qweb_context = {
            event: event,
            record: event.record,
            widget: this,
        };
        this.qweb_context = qweb_context;
        if (_.isEmpty(qweb_context.record)) {
            return '';
        } else {
            return (this.qweb || qweb).render("calendar-box", qweb_context);
        }
    },
    /**
     * @private
     * @param {any} record
     * @param {any} fieldName
     * @returns {string}
     */
    _format: function (record, fieldName) {
        var field = this.state.fields[fieldName];
        if (field.type === "one2many" || field.type === "many2many") {
            return field_utils.format[field.type]({data: record[fieldName]}, field);
        } else {
            return field_utils.format[field.type](record[fieldName], field, {forceString: true});
        }
    },
    /**
     * Initialize the main calendar
     *
     * @private
     */
    _initCalendar: function () {
        var self = this;

        this.$calendar = this.$(".o_calendar_widget");

        // This seems like a workaround but apparently passing the locale
        // in the options is not enough. We should initialize it beforehand
        var locale = moment.locale();
        $.fullCalendar.locale(locale);

        //Documentation here : http://arshaw.com/fullcalendar/docs/
        var fc_options = $.extend({}, this.state.fc_options, {
            eventDrop: function (event) {
                self.trigger_up('dropRecord', event);
            },
            eventResize: function (event) {
                self._disposePopovers();
                self.trigger_up('updateRecord', event);
            },
            // Add/Remove a class on hover to style multiple days events.
            // The css ":hover" selector can't be used because these events
            // are rendered using multiple elements.
            eventMouseover: function (event) {
                self.$calendar.find('[data-event-id=' + event.id + ']').addClass('o_cw_custom_hover');
            },
            eventMouseout: function (event) {
                self.$calendar.find('[data-event-id=' + event.id + ']').removeClass('o_cw_custom_hover');
            },
            eventDragStart: function () {
                self._disposePopovers();
            },
            eventResizeStart: function () {
                self._disposePopovers();
            },
            eventClick: function (event, jsEvent) {
                self._disposePopovers();
                self._renderPopover(event, $(jsEvent.currentTarget));
            },
            select: function (target_date, end_date, event, _js_event, _view) {
                // Clicking on the view, dispose any visible popover.
                // Otherwise create a new event.
                if (_.isElement($('.o_cw_popover')[0])) {
                    self._disposePopovers();
                } else {
                    var data = {'start': target_date, 'end': end_date};
                    if (self.state.context.default_name) {
                        data.title = self.state.context.default_name;
                    }
                    self.trigger_up('openCreate', data);
                }
                self.$calendar.fullCalendar('unselect');
            },
            eventRender: function (event, $fcEvent, view) {
                var start = moment(event.r_start || event.start);
                var end = moment(event.r_end || event.end);
                var $render = $(self._eventRender(event));

                $fcEvent.find('.fc-content').html($render.html());
                $fcEvent.addClass($render.attr('class'));
                $fcEvent.attr('data-event-id', event.id);

                // Detect if the event occurs in just one day
                // note: add & remove 1 min to avoid issues with 00:00
                event.isSameDay = start.clone().add(1, 'minute').isSame(end.clone().subtract(1, 'minute'), 'day');

                // Add background it doesn't exist
                if ($fcEvent.find('.fc-bg').length === 0) {
                    $fcEvent.find('.fc-content').after($('<div/>', {class: "fc-bg"}));
                }

                // Show background for all-day/multidate events only
                if (event.record && view.name === 'month') {
                    if (!event.record.allday && event.isSameDay) {
                        $fcEvent.addClass('o_cw_nobg');
                    }
                }

                // On double click, edit the event
                $fcEvent.bind('dblclick', function(ev) {
                    ev.preventDefault();
                    self._disposePopovers();
                    self.trigger_up('openEvent', event);
                });
            },
            viewRender: function (view) {
                // compute mode from view.name which is either 'month', 'agendaWeek' or 'agendaDay'
                var mode = view.name === 'month' ? 'month' : (view.name === 'agendaWeek' ? 'week' : 'day');
                self.trigger_up('viewUpdated', {
                    mode: mode,
                    title: view.title,
                });
            },
            windowResize: function(view) {
                self._render();
            },
            views: {
                day: {
                    columnFormat: 'LL'
                },
                week: {
                    columnFormat: 'ddd D'
                },
                month: {
                    columnFormat: config.device.isMobile ? 'ddd' : 'dddd'
                }
            },
            height: 'parent',
            unselectAuto: false,
            isRTL: _t.database.parameters.direction === "rtl",
            locale: locale, // reset locale when fullcalendar has already been instanciated before now
        });

        this.$calendar.fullCalendar(fc_options);
    },
    /**
     * Initialize the mini calendar in the sidebar
     *
     * @private
     */
    _initCalendarMini: function () {
        var self = this;
        this.$small_calendar = this.$(".o_calendar_mini");
        this.$small_calendar.datepicker({
            'onSelect': function (datum, obj) {
                self.trigger_up('changeDate', {
                    date: moment(new Date(+obj.currentYear , +obj.currentMonth, +obj.currentDay))
                });
            },
            showOtherMonths: true,
            'dayNamesMin' : this.state.fc_options.dayNamesShort,
            'monthNames': this.state.fc_options.monthNamesShort,
            'firstDay': this.state.fc_options.firstDay,
        });
    },
    /**
     * Initialize the sidebar
     *
     * @private
     */
    _initSidebar: function () {
        this.$sidebar = this.$('.o_calendar_sidebar');
        this.$sidebar_container = this.$(".o_calendar_sidebar_container");
        this._initCalendarMini();
    },
    /**
     * Render the calendar view, this is the main entry point.
     *
     * @override method from AbstractRenderer
     * @private
     * @returns {Deferred}
     */
    _render: function () {
        var $container = this.$el;
        var $calendar = this.$calendar;
        var $fc_view = $calendar.find('.fc-view');
        var scrollPosition = $fc_view.scrollLeft();
        var scrollTop = this.$calendar.find('.fc-scroller').scrollTop();

        $fc_view.scrollLeft(0);
        $calendar.fullCalendar('unselect');

        if (scales[this.state.scale] !== $calendar.data('fullCalendar').getView().type) {
            $calendar.fullCalendar('changeView', scales[this.state.scale]);
        }

        if (this.target_date !== this.state.target_date.toString()) {
            $calendar.fullCalendar('gotoDate', moment(this.state.target_date));
            this.target_date = this.state.target_date.toString();
        }

        this.$small_calendar.datepicker("setDate", this.state.highlight_date.toDate())
                            .find('.o_selected_range')
                            .removeClass('o_color o_selected_range');
        var $a;
        switch (this.state.scale) {
            case 'month': $a = this.$small_calendar.find('td a'); break;
            case 'week': $a = this.$small_calendar.find('tr:has(.ui-state-active) a'); break;
            case 'day': $a = this.$small_calendar.find('a.ui-state-active'); break;
        }
        $a.addClass('o_selected_range');

        $fc_view.scrollLeft(scrollPosition);

        this._renderFilters();

        if (scrollTop) {
            this.$calendar.fullCalendar('reinitView');
        }

        this.$calendar.prependTo(this.$('.o_calendar_view'));
        this._disposePopovers();
        this._renderEvents();

        _.defer(function () {
            $container.height(config.device.isMobile ? $(window).height() - $container.offset().top : '');
            $calendar.fullCalendar('render');
            $a.not('.ui-state-active').addClass('o_color');
        });

        return this._super.apply(this, arguments);
    },
    /**
     * Render all events
     *
     * @private
     */
    _renderEvents: function () {
        this.$calendar.fullCalendar('removeEvents');
        this.$calendar.fullCalendar('addEventSource', this.state.data);
    },
    /**
     * Render all filters
     *
     * @private
     */
    _renderFilters: function () {
        var self = this;
        _.each(this.filters || (this.filters = []), function (filter) {
            filter.destroy();
        });
        _.each(this.state.filters, function (options, index, list) {
            if (!_.find(options.filters, function (f) {return f.display == null || f.display;})) {
                return;
            }
            options.onlyFilter = Object.keys(list).length === 1;
            options.getColor = self.getColor.bind(self);
            options.fields = self.state.fields;
            var filter = new SidebarFilter(self, options);
            filter.appendTo(self.$sidebar);
            self.filters.push(filter);
        });
        _.each(this.$sidebar.find('.o_calendar_filter_item'), function (el) {
            var $filter = $(el);
            // Render popover if an avatar is provided...
            if ($filter.find('.o_cw_filter_avatar').is('img')) {
                $filter.popover({
                    animation: false,
                    content: $filter.find('.o_cw_filter_avatar').clone().addClass('d-block mx-auto'),
                });
            }
        });
    },
    /**
     * Render popover content
     *
     * @private
     * @param {fullCalendarEvent} event
     * @returns {Object} // The popover content
     */
    _renderPopoverContent: function (event) {
        var start = moment(event.r_start || event.start);
        var end = moment(event.r_end || event.end);

        // Fetch user's preferences
        var dbTimeFormat = _t.database.parameters.time_format.search("%H") != -1 ? 'HH:mm': 'hh:mm a';

        var qweb_context = {
            event: event,
            fields: this.state.fields,
            format: this._format.bind(this),
            read_only_mode: this.read_only_mode,
            record: event.record,
            user_context: session.user_context,
            widget: this,
        };

        // Do not display timing if the event occur across multiple days. Otherwise use user's timing preferences
        if (event.isSameDay && !event.record.allday) {
            qweb_context.displayTime = start.clone().format(dbTimeFormat) + " - " + end.clone().format(dbTimeFormat);

            // Calculate duration and format text
            var durHours = moment.duration(end.diff(start)).hours();
            var durMimut = moment.duration(end.diff(start)).minutes();
            var durHoursKey = (durHours === 1) ? 'h' : 'hh';
            var durMinutKey = (durMimut === 1) ? 'm' : 'mm';

            var localeData = moment.localeData(); // i18n for 'hours' and "minutes" strings
            var duration = (durHours > 0 ? localeData.relativeTime(durHours, true, durHoursKey) : '')
                         + (durHours > 0 && durMimut > 0 ? ", " : '')
                         + (durMimut > 0 ? localeData.relativeTime(durMimut, true, durMinutKey) : '');

            qweb_context.displayTimeDur = duration;
        }

        if (!event.isSameDay && start.clone().isSame(end, 'month')) {
            // Simplify date-range if an event occurs into the same month (eg. '4-5 August 2019')
            qweb_context.displayDate = start.clone().format('MMMM D') + "-" + end.clone().format('D, YYYY');
        } else {
            qweb_context.displayDate = event.isSameDay ? start.clone().format('dddd, LL') : start.clone().format('LL') + " - " + end.clone().format('LL');
        }

        if (event.record.allday && event.isSameDay) {
            qweb_context.displayDateDur = _t("All day");
        } else if (event.record.allday && !event.isSameDay) {
            var daysLocaleData = moment.localeData();
            var days = moment.duration(end.diff(start)).days();

            qweb_context.displayDateDur = daysLocaleData.relativeTime(days, true, 'dd');
        }

        this.qweb_context = qweb_context;
        if (_.isEmpty(qweb_context.record)) {
            return '';
        } else {
            return (this.qweb || qweb).render("CalendarView.event.popover", qweb_context);
        }
    },
    /**
     * Render popovers
     *
     * @private
     * @param {fullCalendarEvent} event
     * @param {jQueryElement} $event
     */
    _renderPopover: function (event, $event) {
        var self = this;
        var popoverContent = this._renderPopoverContent(event);
        var popoverContainer = event.allDay ?  '.fc-view' : '.fc-scroller';

        self.$calendar.find('[data-event-id=' + event.id + ']').addClass('o_cw_custom_hilight');

        $event.popover({
            animation: false,
            delay: {
                "show": 50,
                "hide": 100
            },
            trigger: "manual",
            html : true,
            title: event.record.display_name,
            template: popoverContent,
            container: popoverContainer,
        }).popover('show');

        var $popover = $($event.data('bs.popover').tip);

        $popover.find('.o_cw_popover_close').on('click', function () {
            self._disposePopovers();
        });

        $popover.find('.o_cw_popover_edit').on('click', function (ev) {
            self._disposePopovers();
            self.trigger_up('openEvent', event);
            self.$calendar.fullCalendar('unselect');
        });

        $popover.find('.o_cw_popover_delete').on('click', function (ev) {
            self._disposePopovers();

            // TODO: It should remove the record, currently we just unselect
            // ================================================================
                        self.$calendar.fullCalendar('unselect');
            // ================================================================

        });
    },
    /**
     * Dispose popovers for events and filters
     *
     * @private
     */
    _disposePopovers: function () {
        this.$el.find('.fc-event').add('.o_calendar_filter_item')
            .removeClass('o_cw_custom_hilight')
            .popover('dispose');
    },
});

});
