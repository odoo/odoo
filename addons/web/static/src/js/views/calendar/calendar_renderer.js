odoo.define('web.CalendarRenderer', function (require) {
"use strict";

var AbstractRenderer = require('web.AbstractRenderer');
var relational_fields = require('web.relational_fields');
var FieldManagerMixin = require('web.FieldManagerMixin');
var field_utils = require('web.field_utils');
var session = require('web.session');
var Dialog = require('web.Dialog');
var Widget = require('web.Widget');
var utils = require('web.utils');
var core = require('web.core');
var QWeb = require('web.QWeb');

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
    },
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
                        can_create: false,
                    });
            });
            defs.push(def);
        }
        return $.when.apply($, defs);

    },
    start: function () {
        this._super();
        if (this.many2one) {
            this.many2one.appendTo(this.$el);
            this.many2one.filter_ids = _.without(_.pluck(this.filters, 'value'), 'all');
        }
        this.$el.on('click', '.o_remove', this._onFilterRemove.bind(this));
        this.$el.on('click', '.o_checkbox input', this._onFilterActive.bind(this));
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @param {OdooEvent} event
     */
    _onFieldChanged: function (event) {
        var self = this;
        event.stopPropagation();
        var value = event.data.changes[this.write_field].id;
        this._rpc({
                model: this.write_model,
                method: 'create',
                args: [{'user_id': session.uid,'partner_id': value,}],
            })
            .then(function () {
                self.trigger_up('changeFilter', {
                    'fieldName': self.fieldName,
                    'value': value,
                    'active': true,
                });
            });
    },
    _onFilterActive: function (e) {
        var $input = $(e.currentTarget);
        this.trigger_up('changeFilter', {
            'fieldName': this.fieldName,
            'value': $input.closest('.o_calendar_filter_item').data('value'),
            'active': $input.prop('checked'),
        });
    },
    /**
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
    events: _.extend({}, AbstractRenderer.prototype.events, {
        'click .o_calendar_sidebar_toggler': '_onToggleSidebar',
    }),

    /**
     * @constructor
     * @param {Widget} parent
     * @param {Object} state
     * @param {Object} params
     */
    init: function (parent, state, params) {
        this._super.apply(this, arguments);
        this.displayFields = params.displayFields;
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

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @param {any} event
     * @returns {string} the html for the rendered event
     */
    _eventRender: function (event) {
        var qweb_context = {
            event: event,
            record: event.record,
            widget: this,
            read_only_mode: this.read_only_mode,
            user_context: session.user_context,
            format: this._format.bind(this),
            fields: this.state.fields
        };
        this.qweb_context = qweb_context;
        if (_.isEmpty(qweb_context.record)) {
            return '';
        } else {
            return (this.qweb || qweb).render("calendar-box", qweb_context);
        }
    },
    /**
     * @param {any} record
     * @param {any} fieldName
     * @returns {string}
     */
    _format: function (record, fieldName) {
        var field = this.state.fields[fieldName];
        return field_utils.format[field.type](record[fieldName], field);
    },
    /**
     * Initialize the main calendar
     */
    _initCalendar: function () {
        var self = this;

        this.$calendar = this.$(".o_calendar_widget");

        //Documentation here : http://arshaw.com/fullcalendar/docs/
        var fc_options = $.extend({}, this.state.fc_options, {
            eventDrop: function (event) {
                self.trigger_up('dropRecord', event);
            },
            eventResize: function (event) {
                self.trigger_up('updateRecord', event);
            },
            eventClick: function (event) {
                self.trigger_up('openEvent', event);
                self.$calendar.fullCalendar('unselect');
            },
            select: function (target_date, end_date, event, _js_event, _view) {
                self.trigger_up('openCreate', {'start': target_date, 'end': end_date});
                self.$calendar.fullCalendar('unselect');
            },
            eventRender: function (event, element) {
                var $render = $(self._eventRender(event));
                event.title = $render.find('.o_field_type_char:first').text();
                element.find('.fc-content').html($render.html());
                element.addClass($render.attr('class'));
                var display_hour = (event.start.format('HH:mm') === '00:00' ? event.r_start.format('HH:mm') : event.start.format('HH:mm')) + ' - ' +
                    (event.end && event.end.format('HH:mm') !== '00:00' ? event.end.format('HH:mm') : event.r_end.format('HH:mm'));
                if (display_hour === '00:00 - 00:00') {
                    display_hour = _t('All the day');
                }
                element.find('.fc-content .fc-time').text(display_hour);
            },

            unselectAuto: false,
        });

        this.$calendar.fullCalendar(fc_options);
    },
    /**
     * Initialize the mini calendar in the sidebar
     */
    _initCalendarMini: function () {
        var self = this;
        this.$small_calendar = this.$(".o_calendar_mini");
        this.$small_calendar.datepicker({
            'onSelect': function (datum, obj) {
                self.trigger_up('changeDate', {
                    date: new Date(+obj.currentYear , +obj.currentMonth, +obj.currentDay).toString()
                });
            },
            'dayNamesMin' : this.state.fc_options.dayNamesShort,
            'monthNames': this.state.fc_options.monthNamesShort,
            'firstDay': this.state.fc_options.firstDay,
        });
    },
    /**
     * Initialize the sidebar
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
     * @returns {Deferred}
     */
    _render: function () {
        var $calendar = this.$calendar;
        var $fc_view = $calendar.find('.fc-view');
        var scrollPosition = $fc_view.scrollLeft();

        $fc_view.scrollLeft(0);
        $calendar.fullCalendar('unselect');

        if (scales[this.state.scale] !== $calendar.data('fullCalendar').getView().type) {
            $calendar.fullCalendar('changeView', scales[this.state.scale]);
        }

        if (this.target_date !== this.state.target_date.toString()) {
            $calendar.fullCalendar('gotoDate', moment(this.state.target_date));
            this.target_date = this.state.target_date.toString();
        }

        var highlightDate = moment(this.state.highlight_date).format('YYYY-MM-DD');
        $calendar.find('.o_target_date').removeClass('o_target_date');
        $calendar.find('.fc-bg .fc-day[data-date="'+highlightDate+'"]')
                 .addClass('o_target_date');

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
        setTimeout(function () {
            $a.not('.ui-state-active').addClass('o_color');
        });

        $fc_view.scrollLeft(scrollPosition);

        var fullWidth = this.state.fullWidth;
        this.$('.o_calendar_sidebar_toggler')
            .toggleClass('fa-close', !fullWidth)
            .toggleClass('fa-chevron-left', fullWidth)
            .attr('title', !fullWidth ? _('Close Sidebar') : _('Open Sidebar'));
        this.$sidebar_container.toggleClass('o_sidebar_hidden', fullWidth);
        this.$sidebar.toggleClass('o_hidden', fullWidth);

        this._renderFilters();
        this.$calendar.appendTo('body');
        this.$calendar.fullCalendar('render');
        this._renderEvents();
        this.$calendar.prependTo(this.$('.o_calendar_view'));

        return this._super.apply(this, arguments);
    },
    /**
     * Render all events
     */
    _renderEvents: function () {
        this.$calendar.fullCalendar('removeEvents');
        this.$calendar.fullCalendar('addEventSource', this.state.data);
    },
    /**
     * Render all filters
     */
    _renderFilters: function () {
        var self = this;
        _.each(this.filters || (this.filters = []), function (filter) {
            filter.destroy();
        });
        if (this.state.fullWidth) {
            return;
        }
        _.each(this.state.filters, function (options) {
            if (!_.find(options.filters, function (f) {return f.display == null || f.display;})) {
                return;
            }
            options.getColor = self.getColor.bind(self);
            options.fields = self.state.fields;
            var filter = new SidebarFilter(self, options);
            filter.appendTo(self.$sidebar);
            self.filters.push(filter);
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Toggle the sidebar
     */
    _onToggleSidebar: function () {
        this.trigger_up('toggleFullWidth');
    },
});

});
