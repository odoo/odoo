odoo.define('web.CalendarView', function (require) {
"use strict";

var AbstractView = require('web.AbstractView');
var CalendarModel = require('web.CalendarModel');
var CalendarController = require('web.CalendarController');
var CalendarRenderer = require('web.CalendarRenderer');
var core = require('web.core');
var utils = require('web.utils');

var _lt = core._lt;

// gather the fields to get
var fieldsToGather = [
    "date_start",
    "date_delay",
    "date_stop",
    "all_day",
];

var CalendarView = AbstractView.extend({
    display_name: _lt('Calendar'),
    icon: 'fa-calendar',
    jsLibs: ['/web/static/lib/fullcalendar/js/fullcalendar.js'],
    cssLibs: ['/web/static/lib/fullcalendar/css/fullcalendar.css'],
    config: {
        Model: CalendarModel,
        Controller: CalendarController,
        Renderer: CalendarRenderer,
    },
    viewType: 'calendar',
    groupable: false,

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
            if (!child.attrs.invisible) {
                displayFields[fieldName] = child.attrs;

                if (params.sidebar === false) return; // if we have not sidebar, (eg: Dashboard), we don't use the filter "coworkers"

                if (child.attrs.avatar_field) {
                    filters[fieldName] = filters[fieldName] || {
                        'title': fields[fieldName].string,
                        'fieldName': fieldName,
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
                    };
                    filters[fieldName].write_model = child.attrs.write_model;
                    filters[fieldName].write_field = child.attrs.write_field; // can't use a x2many fields

                    modelFilters.push(fields[fieldName].relation);
                }
            }
        });

        if (attrs.color) {
            var fieldName = attrs.color;
            fieldNames.push(fieldName);
            filters[fieldName] = {
                'title': fields[fieldName].string,
                'fieldName': fieldName,
                'filters': [],
            };
            if (fields[fieldName].relation) {
                if (['res.users', 'res.partner'].indexOf(fields[fieldName].relation) !== -1) {
                    filters[fieldName].avatar_field = 'image_small';
                }
                filters[fieldName].avatar_model = fields[fieldName].relation;
            }
        }

        if (_.isEmpty(displayFields)) {
            displayFields = fields.display_name ? {'display_name': {}} : [];
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

        this.controllerParams.readonlyFormViewId = !attrs.readonly_form_view_id || !utils.toBoolElse(attrs.readonly_form_view_id, true) ? false : attrs.readonly_form_view_id;
        this.controllerParams.eventOpenPopup = utils.toBoolElse(attrs.event_open_popup || '', false);
        this.controllerParams.mapping = mapping;
        this.controllerParams.context = params.context || {};
        this.controllerParams.displayName = params.action && params.action.name;

        this.rendererParams.displayFields = displayFields;
        this.rendererParams.eventTemplate = _.findWhere(arch.children, {'tag': 'templates'});
        this.rendererParams.model = viewInfo.model;

        this.loadParams.fieldNames = _.uniq(fieldNames);
        this.loadParams.mapping = mapping;
        this.loadParams.fields = fields;
        this.loadParams.fieldsInfo = viewInfo.fieldsInfo;
        this.loadParams.editable = !fields[mapping.date_start].readonly;
        this.loadParams.creatable = true;
        this.loadParams.eventLimit = eventLimit;
        this.loadParams.fieldColor = attrs.color;

        this.loadParams.filters = filters;
        this.loadParams.mode = (params.context && params.context.default_mode) || attrs.mode;
        this.loadParams.initialDate = moment(params.initialDate || new Date());
    },
});

return CalendarView;

});
