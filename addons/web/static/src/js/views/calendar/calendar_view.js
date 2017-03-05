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
    config: {
        Model: CalendarModel,
        Controller: CalendarController,
        Renderer: CalendarRenderer,
    },
    init: function (arch, fields, params) {
        this._super.apply(this, arguments);
        var attrs = arch.attrs;

        if (!attrs.date_start) {
            throw new Error(_t("Calendar view has not defined 'date_start' attribute."));
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

        if (attrs.color) {
            fieldNames.push(attrs.color.split('.')[0]);
        }

        var eventLimit = attrs.event_limit !== null && (isNaN(+attrs.event_limit) ? _.str.toBool(attrs.event_limit) : +attrs.event_limit);

        var filters = {};

        _.each(arch.children, function (child) {
            switch (child.tag) {
                case "filter":
                    if (params.sidebar === false) break; // if we have not sidebar, (eg: Dashboard), we don't use the filter "coworkers"
                    var fieldName = child.attrs.name;
                    filters[fieldName] = {
                        'title': fields[fieldName].string,
                        'fieldName': fieldName,
                        'filters': [],
                    };
                    if (child.attrs.avatar_field) {
                        filters[fieldName].avatar_field = child.attrs.avatar_field;
                        filters[fieldName].avatar_model = fields[fieldName].relation;
                    }
                    if (child.attrs.write_model) {
                        filters[fieldName].write_model = child.attrs.write_model;
                        filters[fieldName].write_field = child.attrs.write_field; // can't use a x2many fields
                    }
                    fieldNames.push(child.attrs.name);
                    break;
                case "field":
                    fieldNames.push(child.attrs.name);
                    if (!child.attrs.invisible) {
                        displayFields[child.attrs.name] = child.attrs;
                    }
            }
        });

        if (_.isEmpty(displayFields)) {
            displayFields = fields.display_name ? {'display_name': {}} : [];
        }

        //if quick_add = False, we don't allow quick_add
        //if quick_add = not specified in view, we use the default widgets.QuickCreate
        //if quick_add = is NOT False and IS specified in view, we this one for widgets.QuickCreate'   
        this.controllerParams.quick_add_pop = (attrs.quick_add || utils.toBoolElse(attrs.quick_add+'', true));
        this.controllerParams.disable_quick_create =  params.disable_quick_create || !this.controllerParams.quick_add_pop;
        this.controllerParams.confirm_on_delete = true;
        // If this field is set ot true, we don't open the event in form view, but in a popup with the view_id passed by this parameter
        this.controllerParams.formViewId = !attrs.form_view_id || !utils.toBoolElse(attrs.form_view_id, true) ? false : attrs.form_view_id;
        this.controllerParams.readonlyFormViewId = !attrs.readonly_form_view_id || !utils.toBoolElse(attrs.readonly_form_view_id, true) ? false : attrs.readonly_form_view_id;
        this.controllerParams.mapping = mapping;
        this.controllerParams.context = params.context || {};

        this.rendererParams.displayFields = displayFields;
        this.rendererParams.eventTemplate = _.findWhere(arch.children, {'tag': 'template'});

        this.loadParams.fieldNames = _.uniq(fieldNames);
        this.loadParams.mapping = mapping;
        this.loadParams.fields = fields;
        this.loadParams.editable = !this.controllerParams.read_only_mode && !fields[mapping.date_start].readonly;
        this.loadParams.eventLimit = eventLimit;
        this.loadParams.field_color = attrs.color;

        this.loadParams.filters = filters;
        this.loadParams.mode = attrs.mode;
        this.loadParams.scale_zoom = attrs.scale_zoom;
        this.loadParams.initialDate = params.initialDate || new Date();

        // is_action_enabled: function (action) {
        //     if (action === 'create' && !this.options.creatable) {
        //         return false;
        //     }
        //     return this._super(action);
        // },


    },
});

return CalendarView;

});
