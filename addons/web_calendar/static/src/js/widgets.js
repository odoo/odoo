odoo.define('web_calendar.widgets', function(require) {
"use strict";

var core = require('web.core');
var data = require('web.data');
var Dialog = require('web.Dialog');
var form_common = require('web.form_common');
var Widget = require('web.Widget');

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
var QuickCreate = Widget.extend({
    init: function(parent, dataset, buttons, options, data_template) {
        this._super(parent);
        this.dataset = dataset;
        this._buttons = buttons || false;
        this.options = options;

        // Can hold data pre-set from where you clicked on agenda
        this.data_template = data_template || {};
        this.$input = $();
    },
    get_title: function () {
        var parent = this.getParent();
        if (_.isUndefined(parent)) {
            return _t("Create");
        }
        var title = (_.isUndefined(parent.field_widget)) ?
                (parent.string || parent.name) :
                parent.field_widget.string || parent.field_widget.name || '';
        return _t("Create: ") + title;
    },
    start: function () {
        var self = this;

        if (this.options.disable_quick_create) {
            this.slow_create();
            return;
        }
        self.on('added', self, function() {
            self.trigger('close');
        });

        this.$dialog = new Dialog(this, {
            title: this.get_title(),
            size: 'small',
            buttons: this._buttons ? [
                {text: _t("Create event"), oe_link_class: 'oe_highlight', click: function (e) {
                    if (!self.quick_add()) {
                        self.focus();
                    }
                }},
                {text: _t("Edit event"), oe_link_class: 'oe_link', click: function (e) {
                    self.slow_add();
                }}
            ] : []
        }, QWeb.render('CalendarView.quick_create', {widged: this}))
        .on('closed', self, function() {
            self.trigger('close');
        })
        .open();
        this.$input = this.$dialog.$('input').keyup(function enterHandler (e) {
            if(e.keyCode == 13){
                self.$input.off('keyup', enterHandler);
                if (!self.quick_add()){
                    self.$input.on('keyup', enterHandler);
                }
            } else if (e.keyCode == 27 && self._buttons) {
                self.trigger('close');
            }
        });
    },
    focus: function() {
        this.$input.focus();
    },

    /**
     * Gathers data from the quick create dialog a launch quick_create(data) method
     */
    quick_add: function() {
        var val = this.$input.val();
        if (/^\s*$/.test(val)) {
            return false;
        }
        return this.quick_create({'name': val}).always(function() { return true; });
    },
    
    slow_add: function() {
        var val = this.$input.val();
        this.slow_create({'name': val});
    },

    /**
     * Handles saving data coming from quick create box
     */
    quick_create: function(data, options) {
        var self = this;
        return this.dataset.create($.extend({}, this.data_template, data), options)
            .then(function(id) {
                self.trigger('added', id);
                self.$input.val("");
            }).fail(function(r, event) {
                event.preventDefault();
                // This will occurs if there are some more fields required
                self.slow_create(data);
            });
    },

    /**
     * Show full form popup
     */
     get_form_popup_infos: function() {
        var parent = this.getParent();
        var infos = {
            view_id: false,
            title: this.name,
        };
        if (!_.isUndefined(parent) && !(_.isUndefined(parent.ViewManager))) {
            infos.view_id = parent.ViewManager.get_view_id('form');
        }
        return infos;
    },
    slow_create: function(_data) {
        //if all day, we could reset time to display 00:00:00
        
        var self = this;
        var def = $.Deferred();
        var defaults = {};
        var created = false;

        _.each($.extend({}, this.data_template, _data), function(val, field_name) {
            defaults['default_' + field_name] = val;
        });
                    
        var pop_infos = self.get_form_popup_infos();
        var pop = new form_common.FormOpenPopup(this);
        var context = new data.CompoundContext(this.dataset.context, defaults);
        pop.show_element(this.dataset.model, null, this.dataset.get_context(defaults), {
            title: this.get_title(),
            disable_multiple_selection: true,
            view_id: pop_infos.view_id,
            // Ensuring we use ``self.dataset`` and DO NOT create a new one.
            create_function: function(data, options) {
                return self.dataset.create(data, options).done(function(r) {
                }).fail(function (r, event) {
                   if (!r.data.message) { //else manage by openerp
                        throw new Error(r);
                   }
                });
            },
            read_function: function(id, fields, options) {
                return self.dataset.read_ids.apply(self.dataset, arguments).done(function() {
                }).fail(function (r, event) {
                    if (!r.data.message) { //else manage by openerp
                        throw new Error(r);
                    }
                });
            },
        });
        pop.on('closed', self, function() {
            // ``self.trigger('close')`` would itself destroy all child element including
            // the slow create popup, which would then re-trigger recursively the 'closed' signal.  
            // Thus, here, we use a deferred and its state to cut the endless recurrence.
            if (def.state() === "pending") {
                def.resolve();
            }
        });
        pop.on('create_completed', self, function(id) {
            created = true;
            self.trigger('slowadded');
        });
        def.then(function() {
            if (created) {
                var parent = self.getParent();
                parent.$calendar.fullCalendar('refetchEvents');
            }
            self.trigger('close');
        });
        return def;
    },
});

/**
 * Common part to manage any field using calendar view
 */
var Sidebar = Widget.extend({
    template: 'CalendarView.sidebar',
    
    start: function() {
        this._super();
        this.filter = new SidebarFilter(this, this.getParent());
        this.filter.appendTo(this.$el.find('.oe_calendar_filter'));
    }
});
var SidebarFilter = Widget.extend({
    events: {
        'change input:checkbox': 'filter_click',
        'click span.color_filter': 'select_previous',

    },
    init: function(parent, view) {
        this._super(parent);
        this.view = view;
    },
    set_filters: function() {
        var self = this;
        _.forEach(self.view.all_filters, function(o) {
            if (_.contains(self.view.now_filter_ids, o.value)) {
                self.$('div.oe_calendar_responsible input[value=' + o.value + ']').prop('checked',o.is_checked);
            }
        });
    },
    events_loaded: function(filters) {
        var self = this;
        if (!filters) {
            filters = [];
            _.forEach(self.view.all_filters, function(o) {
                if (_.contains(self.view.now_filter_ids, o.value)) {
                    filters.push(o);
                }
            });
        }            
        this.$el.html(QWeb.render('CalendarView.sidebar.responsible', { filters: filters }));
    },
    filter_click: function(e) {
        var self = this;
        if (self.view.all_filters[0] && e.target.value == self.view.all_filters[0].value) {
            self.view.all_filters[0].is_checked = e.target.checked;
        } else {
            self.view.all_filters[e.target.value].is_checked = e.target.checked;
        }
        self.view.$calendar.fullCalendar('refetchEvents');
    },
    select_previous: function(e) {
        $(e.target).siblings('input').trigger('click');
    }
});

return {
    QuickCreate: QuickCreate,
    Sidebar: Sidebar,
    SidebarFilter: SidebarFilter
};

});
