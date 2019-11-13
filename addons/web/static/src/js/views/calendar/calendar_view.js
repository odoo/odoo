odoo.define('web.CalendarView', async function (require) {
    "use strict";

    const AbstractView = require('web.AbstractView');
    const CalendarController = require('web.CalendarController');
    const CalendarModel = require('web.CalendarModel');
    const CalendarRenderer = require('web.CalendarRenderer');
    const core = require('web.core');
    const pyUtils = require('web.py_utils');
    const RendererWrapper = require('web.RendererWrapper');
    const utils = require('web.utils');

    const _lt = core._lt;

    // gather the fields to get
    const fieldsToGather = [
        "date_start",
        "date_delay",
        "date_stop",
        "all_day",
    ];

    const CalendarView = AbstractView.extend({
        display_name: _lt('Calendar'),
        icon: 'fa-calendar',
        jsLibs: ['/web/static/lib/fullcalendar/js/fullcalendar.js'],
        cssLibs: ['/web/static/lib/fullcalendar/css/fullcalendar.css'],
        config: Object.assign({}, AbstractView.prototype.config, {
            Model: CalendarModel,
            Controller: CalendarController,
            Renderer: CalendarRenderer,
        }),
        viewType: 'calendar',
        searchMenuTypes: ['filter', 'favorite'],

        /**
         * @override
         */
        init(viewInfo, params) {
            this._super(...arguments);
            const arch = this.arch;
            const fields = this.fields;
            const attrs = arch.attrs;

            if (!attrs.date_start) {
                throw new Error(_lt("Calendar view has not defined 'date_start' attribute."));
            }

            const mapping = {};
            const fieldNames = fields.display_name ? ['display_name'] : [];
            const displayFields = {};

            fieldsToGather.forEach(field =>  {
                if (arch.attrs[field]) {
                    const fieldName = attrs[field];
                    mapping[field] = fieldName;
                    fieldNames.push(fieldName);
                }
            });

            const filters = {};

            const eventLimit = attrs.event_limit !== null && (isNaN(+attrs.event_limit) ? _.str.toBool(attrs.event_limit) : +attrs.event_limit);

            const modelFilters = []; // TODO: MSH: Is it used anywhere?
            arch.children.forEach(child => {
                if (child.tag !== 'field') {
                    return;
                }
                const fieldName = child.attrs.name;
                fieldNames.push(fieldName);
                if (!child.attrs.invisible || child.attrs.filters) {
                    child.attrs.options = child.attrs.options ? pyUtils.py_eval(child.attrs.options) : {};
                    if (!child.attrs.invisible) {
                        displayFields[fieldName] = {attrs: child.attrs};
                    }

                    if (params.sidebar === false) {
                        return; // if we have not sidebar, (eg: Dashboard), we don't use the filter "coworkers"
                    }

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
                    if (child.attrs.filters) {
                        filters[fieldName] = filters[fieldName] || {
                            'title': fields[fieldName].string,
                            'fieldName': fieldName,
                            'filters': [],
                        };
                        if (child.attrs.color) {
                            filters[fieldName].field_color = child.attrs.color;
                            filters[fieldName].color_model = fields[fieldName].relation;
                        }
                        if (!child.attrs.avatar_field && fields[fieldName].relation) {
                            if (fields[fieldName].relation.includes(['res.users', 'res.partner', 'hr.employee'])) {
                                filters[fieldName].avatar_field = 'image_128';
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
            this.controllerParams.quickAddPop = (!('quick_add' in attrs) || utils.toBoolElse(attrs.quick_add + '', true));
            this.controllerParams.disableQuickCreate = params.disable_quick_create || !this.controllerParams.quickAddPop;

            // If form_view_id is set, then the calendar view will open a form view
            // with this id, when it needs to edit or create an event.
            this.controllerParams.formViewId =
                attrs.form_view_id ? parseInt(attrs.form_view_id, 10) : false;
            if (!this.controllerParams.formViewId && params.action) {
                const formViewDescr = params.action.views.find(v => {
                    return v.type === 'form';
                });
                if (formViewDescr) {
                    this.controllerParams.formViewId = formViewDescr.viewID;
                }
            }

            this.controllerParams.eventOpenPopup = utils.toBoolElse(attrs.event_open_popup || '', false);
            this.controllerParams.showUnusualDays = utils.toBoolElse(attrs.show_unusual_days || '', false);
            this.controllerParams.mapping = mapping;
            this.controllerParams.context = params.context || {};
            this.controllerParams.displayName = params.action && params.action.name;

            this.rendererParams.displayFields = displayFields;
            this.rendererParams.model = viewInfo.model;
            this.rendererParams.hideDate = utils.toBoolElse(attrs.hide_date || '', false);
            this.rendererParams.hideTime = utils.toBoolElse(attrs.hide_time || '', false);
            this.rendererParams.canDelete = this.controllerParams.activeActions.delete;

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
            this.loadParams.initialDate = moment(params.initialDate || new Date());
        },
        /**
         * Returns a new renderer instance
         *
         * @param {Widget} parent the parent of the renderer
         * @param {Object} state the information related to the rendered data
         * @returns {Renderer} instance of the renderer
         */
        getRenderer(parent, state) {
            state = Object.assign(state || {}, this.rendererParams);
            return new RendererWrapper(null, this.config.Renderer, state);
        },
    });

    return CalendarView;

});
