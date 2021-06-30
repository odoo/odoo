odoo.define('web.CalendarView', function (require) {
"use strict";

var AbstractView = require('web.AbstractView');
var CalendarModel = require('web.CalendarModel');
var CalendarController = require('web.CalendarController');
var CalendarRenderer = require('web.CalendarRenderer');
var core = require('web.core');
var pyUtils = require('web.py_utils');
var utils = require('web.utils');

var _lt = core._lt;

// gather the fields to get
var fieldsToGather = [
    "date_start",
    "date_delay",
    "date_stop",
    "all_day",
    "recurrence_update",
    "create_name_field",
];

const scalesInfo = {
    day: 'timeGridDay',
    week: 'timeGridWeek',
    month: 'dayGridMonth',
    year: 'dayGridYear',
};

var CalendarView = AbstractView.extend({
    display_name: _lt('Calendar'),
    icon: 'fa-calendar',
    jsLibs: [
        '/web/static/lib/fullcalendar/core/main.js',
        '/web/static/lib/fullcalendar/interaction/main.js',
        '/web/static/lib/fullcalendar/moment/main.js',
        '/web/static/lib/fullcalendar/daygrid/main.js',
        '/web/static/lib/fullcalendar/timegrid/main.js',
        '/web/static/lib/fullcalendar/list/main.js'
    ],
    cssLibs: [
        '/web/static/lib/fullcalendar/core/main.css',
        '/web/static/lib/fullcalendar/daygrid/main.css',
        '/web/static/lib/fullcalendar/timegrid/main.css',
        '/web/static/lib/fullcalendar/list/main.css'
    ],
    config: _.extend({}, AbstractView.prototype.config, {
        Model: CalendarModel,
        Controller: CalendarController,
        Renderer: CalendarRenderer,
    }),
    viewType: 'calendar',
    searchMenuTypes: ['filter', 'favorite'],

    /**
     * @override
     */
    init: function (viewInfo, params) {
        this._super.apply(this, arguments);
        var arch = this.arch;
        var fields = this.fields;
        var attrs = arch.attrs;

        if (!attrs.date_start) {
            throw new Error(_lt("Calendar view has not defined 'date_start' attribute."));
        }

        var mapping = {};
        var fieldNames = fields.display_name ? ['display_name'] : [];
        var displayFields = {};
        let popoverFields = {};

        _.each(fieldsToGather, function (field) {
            if (arch.attrs[field]) {
                var fieldName = attrs[field];
                mapping[field] = fieldName;
                fieldNames.push(fieldName);
            }
        });

        var filters = {};

        var eventLimit = attrs.event_limit !== null && (isNaN(+attrs.event_limit) ? _.str.toBool(attrs.event_limit) : +attrs.event_limit);

        var modelFilters = [];
        _.each(arch.children, function (child) {
            if (child.tag !== 'field') return;
            var fieldName = child.attrs.name;
            fieldNames.push(fieldName);
            popoverFields[fieldName] = {attrs: child.attrs};
            if (!child.attrs.invisible || child.attrs.filters) {
                child.attrs.options = child.attrs.options ? pyUtils.py_eval(child.attrs.options) : {};
                if (!child.attrs.invisible) {
                    displayFields[fieldName] = {attrs: child.attrs};
                }

                if (params.sidebar === false) return; // if we have not sidebar, (eg: Dashboard), we don't use the filter "coworkers"

                if (child.attrs.avatar_field) {
                    filters[fieldName] = filters[fieldName] || {
                        'title': fields[fieldName].string,
                        'fieldName': fieldName,
                        'filters': [],
                        'check_all': {},
                        'filters': [],
                    };
                    filters[fieldName].avatar_field = child.attrs.avatar_field;
                    filters[fieldName].avatar_model = fields[fieldName].relation;
                }
                if (child.attrs.write_model) {
                    filters[fieldName] = filters[fieldName] || {
                        'title': fields[fieldName].string,
                        'fieldName': fieldName,
                        'filters': [],
                        'check_all': {},
                    };
                    filters[fieldName].write_model = child.attrs.write_model;
                    filters[fieldName].write_field = child.attrs.write_field; // can't use a x2many fields
                    filters[fieldName].filter_field = child.attrs.filter_field;

                    modelFilters.push(fields[fieldName].relation);
                }
                if (child.attrs.filters) {
                    filters[fieldName] = filters[fieldName] || {
                        'title': fields[fieldName].string,
                        'fieldName': fieldName,
                        'check_all': {},
                        'filters': [],
                    };
                    if (child.attrs.color) {
                        filters[fieldName].field_color = child.attrs.color;
                        filters[fieldName].color_model = fields[fieldName].relation;
                    }
                    if (!child.attrs.avatar_field && fields[fieldName].relation) {
                        if (fields[fieldName].relation.includes(['res.users', 'res.partner', 'hr.employee'])) {
                            filters[fieldName].avatar_field = 'avatar_128';
                        }
                        filters[fieldName].avatar_model = fields[fieldName].relation;
                    }
                }
            }
        });

        if (attrs.color) {
            var fieldName = attrs.color;
            fieldNames.push(fieldName);
        }

        //if quick_add = False, we don't allow quick_add
        //if quick_add = not specified in view, we use the default widgets.QuickCreate
        //if quick_add = is NOT False and IS specified in view, we this one for widgets.QuickCreate'
        this.controllerParams.quickAddPop = (!('quick_add' in attrs) || utils.toBoolElse(attrs.quick_add+'', true));
        this.controllerParams.disableQuickCreate =  params.disable_quick_create || !this.controllerParams.quickAddPop;

        // If form_view_id is set, then the calendar view will open a form view
        // with this id, when it needs to edit or create an event.
        this.controllerParams.formViewId =
            attrs.form_view_id ? parseInt(attrs.form_view_id, 10) : false;
        if (!this.controllerParams.formViewId && params.action) {
            var formViewDescr = _.find(params.action.views, function (v) {
                return v.type ===  'form';
            });
            if (formViewDescr) {
                this.controllerParams.formViewId = formViewDescr.viewID;
            }
        }

        let scales;
        const allowedScales = Object.keys(scalesInfo);
        if (arch.attrs.scales) {
            scales = arch.attrs.scales.split(',')
                .filter(x => allowedScales.includes(x));
        } else {
            scales = allowedScales;
        }

        this.controllerParams.eventOpenPopup = utils.toBoolElse(attrs.event_open_popup || '', false);
        this.controllerParams.showUnusualDays = utils.toBoolElse(attrs.show_unusual_days || '', false);
        this.controllerParams.mapping = mapping;
        this.controllerParams.context = params.context || {};
        this.controllerParams.displayName = params.action && params.action.name;
        this.controllerParams.scales = scales;

        this.rendererParams.displayFields = displayFields;
        this.rendererParams.popoverFields = popoverFields;
        this.rendererParams.model = viewInfo.model;
        this.rendererParams.hideDate = utils.toBoolElse(attrs.hide_date || '', false);
        this.rendererParams.hideTime = utils.toBoolElse(attrs.hide_time || '', false);
        this.rendererParams.canDelete = this.controllerParams.activeActions.delete;
        this.rendererParams.canCreate = this.controllerParams.activeActions.create;
        this.rendererParams.scalesInfo = scalesInfo;

        this.loadParams.fieldNames = _.uniq(fieldNames);
        this.loadParams.mapping = mapping;
        this.loadParams.fields = fields;
        this.loadParams.fieldsInfo = viewInfo.fieldsInfo;
        this.loadParams.editable = !fields[mapping.date_start].readonly;
        this.loadParams.creatable = this.controllerParams.activeActions.create;
        this.loadParams.eventLimit = eventLimit;
        this.loadParams.fieldColor = attrs.color;

        this.loadParams.filters = filters;
        this.loadParams.mode = (params.context && params.context.default_mode) || attrs.mode;
        this.loadParams.scales = scales;
        this.loadParams.initialDate = moment(
            (params.context && params.context.initial_date) ||
            params.initialDate || 
            new Date()
        );
        this.loadParams.scalesInfo = scalesInfo;
    },
});

return CalendarView;

});
