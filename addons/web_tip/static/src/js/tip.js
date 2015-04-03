odoo.define('web_tip.web_tip', function (require) {
"use strict";

var core = require('web.core');
var form_widgets = require('web.form_widgets');
var Model = require('web.DataModel');
var utils = require('web.utils');
var WebClient = require('web.WebClient');
var KanbanView = require('web_kanban.KanbanView');
var kanban_common = require('web_kanban.common');
var Widget = require('web.Widget');
var ListView = require('web.ListView');

var bus = core.bus;
var Class = core.Class;

var Tip = Class.extend({
    init: function() {
        var self = this;
        self.tips = [];
        self.$overlay = null;
        self.$element = null;

        var Tips = new Model('web.tip');
        Tips.query(['title', 'description', 'action_id', 'model', 'type', 'mode',
            'highlight_selector', 'end_event', 'placement', 'is_consumed'])
            .all().then(function(tips) {
                self.tips = tips;
            })
        ;

        core.bus.on('action', this, function(action) {
            self.on_action(action);
        });

        bus.on('view_shown', this, function(view) {
            if (_.keys(view.fields_view).length === 0) {
                view.on('view_loaded', this, function(fields_view) {
                    self.on_view(view);
                });
            } else {
                self.on_view(view);
            }

            view.on('switch_mode', this, function() {
            });
        });

        bus.on('view_switch_mode', this, function(viewManager, mode) {
            self.on_switch(viewManager, mode);
        });
        bus.on('form_view_shown', this, function(formView) {
            self.on_form_view(formView);
        });

        bus.on('form_view_saved', this, function(formView) {
            self.on_form_view(formView);
        });
    },

    // stub
    on_action: function(action) {
        var self = this;
        var action_id = action.id;
        var model = action.res_model;
    },

    on_view: function(view) {
        var self = this;
        var fields_view = view.fields_view;
        var action_id = view.ViewManager.action ? view.ViewManager.action.id : null;
        var model = fields_view.model;

        // kanban
        if(fields_view.type === 'kanban') {
            var dataset_def = $.Deferred();
            var groups_def = $.Deferred();
            view.on("kanban_dataset_processed", self, function() {
                var length = view.dataset.ids.length;
                dataset_def.resolve(length);
            });
            view.on('kanban_groups_processed', self, function() {
                groups_def.resolve();
            });
            view.on('kanban_reset_tip', self, function() {
                $('.oe_breathing').remove();
                self.eval_tip(action_id, model, fields_view.type);
            });
            dataset_def.done(function(length) {
                self.eval_tip(action_id, model, fields_view.type);
            });
            groups_def.done(function() {
                self.eval_tip(action_id, model, fields_view.type);
            });
        } else if (fields_view.type === 'tree' || view.hasOwnProperty('editor')) {
            view.on('view_list_rendered', self, function() {
                self.eval_tip(action_id, model, fields_view.type);
            });
            view.on('list_reset_tip', self, function() {
                self.eval_tip(action_id, model, fields_view.type);
            });
        }
    },

    on_form_view: function(formView) {
        var self = this;
        var model = formView.model;
        var type = formView.datarecord.type ? formView.datarecord.type : null;
        var mode = 'form';
        formView.on('view_content_has_changed', self, _.once(function() {
            self.eval_tip(null, model, mode, type);
        }));
        if ($('.oe_chatter').length > 0) {
            core.bus.on('chatter_messages_fetched', this, _.once(function () {
                self.eval_tip(null, model, mode, type);
            }));
        } else {
            self.eval_tip(null, model, mode, type);
        }
    },

    // stub
    on_switch: function (viewManager, mode) {
        var self = this;
        var action = viewManager.action;
        var action_id = action.id;
        var model = action.res_model;
    },

    eval_tip: function(action_id, model, mode, type) {
        var self = this;
        var filter = {};
        var valid_tips = [];
        var tips = [];
        if (action_id) {
            valid_tips = _.filter(self.tips, function (tip) {
                return tip.action_id[0] === action_id;
            });
        }

        filter.model = model;
        filter.mode = mode;
        tips = _.where(self.tips, filter);
        if (type) {
            tips = _.filter(tips, function(tip) {
                if (!tip.type) {
                    return true;
                }
                return tip.type === type;
            });
        }

        valid_tips = _.uniq(valid_tips.concat(tips));
        _.each(valid_tips, function(tip) {
            if (!tip.is_consumed) {
                self.do_tip(tip);
            }
        });
    },

    do_tip: function (tip) {
        var self = this;
        self.def = $.Deferred();
        var Tips = new Model('web.tip');
        var highlight_selector = tip.highlight_selector;

        if(!$(highlight_selector).length > 0 || !$(highlight_selector).is(":visible")) {
            return self.def.reject();
        }

        self.$element = $(highlight_selector).first();
        if (self.$element.height() === 0 || self.$element.width() === 0) {
            var $images = self.$element.find('img');
            if ($images.length > 0) {
                $images.first().load(function() {
                    self.do_tip(tip);
                });
            }
            return self.def.reject();
        }
        if(!self.$element.next().hasClass('oe_breathing')) {
            self.$element.after('<i class="oe_breathing">');
            self.$element.next().position({ my: "center", at: "center", of: self.$element });
        }
        self.scroll_to_tip();
        self.$helper = $("<div>", { class: 'oe_tip_helper' });
        self.$element.next().one('click', function(e) {
            e.stopImmediatePropagation();
            self.$element = $(tip.highlight_selector).first();
            $(this).addClass('oe_explode');
            self.trigger_tips(tip);
        });

        // resize
        bus.on('resize', this, function() {
            self.reposition();
        });

        bus.on('please_reposition_tip', this, function () {
            self.reposition();
        });
        return self.def;
    },
    trigger_tips: function(tip) {
        var self = this;
        self.$helper = $("<div>", { class: 'oe_tip_helper' });
        self.$element.after(self.$helper);
        self._set_helper_position();

        self.$overlay = $("<div>", { class: 'oe_tip_overlay' });
        $('body').append(self.$overlay);
        self.$element.addClass('oe_tip_show_element');

        // fix the stacking context problem
        _.each(self.$element.parentsUntil('body'), function(el) {
            var zIndex = $(el).css('z-index');
            var opacity = parseFloat($(el).css('opacity'));

            if (/[0-9]+/.test(zIndex) || opacity < 1) {
                $(el).addClass('oe_tip_fix_parent');
            }
        });
        self.$element.popover({
            placement: tip.placement,
            title: tip.title,
            content: tip.description,
            html: true,
            container: 'body',
        }).popover('show');

        var $cross = $('<button type="button" class="close oe_tip_close">&times;</button>');

        if (tip.title) {
            $('.popover-title').prepend($cross);
        } else {
            $('.popover-content').prepend($cross);
        }

        // consume tip
        $(tip.highlight_selector).one(tip.end_event, function($ev) {
            self.end_tip(tip);
            self.def.resolve();
        });

        // dismiss tip
        $cross.on('click', function($ev) {
            self.end_tip(tip);
            self.def.resolve();
        });
        self.$overlay.on('click', function($ev) {
            self.end_tip(tip);
            self.def.resolve();
        });
        $(document).on('keyup.web_tip', function($ev) {
            if ($ev.which === 27) { // esc
                self.end_tip(tip);
                self.def.resolve();
            }
        });
    },

    scroll_to_tip: function(){
        var self = this;
        var scroll = _.find(self.$element.parentsUntil('body'), function(el) {
            var overflow = $(el).css('overflow-y');
            return (overflow === 'auto' || overflow === 'scroll');
        });
        if (scroll) {
            $(scroll).scrollTo(self.$element);
        }
    },

    end_tip: function(tip) {
        var self = this;
        var Tips = new Model('web.tip');
        self.$element.popover('destroy');
        self.$element.removeAttr('style');
        self.$overlay.remove();
        self.$helper.remove();
        self.$element.removeClass('oe_tip_show_element');
        self.$element.next().remove();
        _.each($('.oe_tip_fix_parent'), function(el) {
            $(el).removeClass('oe_tip_fix_parent');
        });
        $(document).off('keyup.web_tip');
        Tips.call('consume', [tip.id], {});
        tip.is_consumed = true;
    },

    reposition: function() {
        var self = this;
        if (self.$element.hasClass('oe_tip_show_element')) {
            self.scroll_to_tip();
            self._set_helper_position();
            self.$element.popover('show');
        }
        if(self.def.state() == 'pending') {
            self._set_tip_position();
        }
    },

    _set_helper_position : function() {
        var offset = this.$element.offset();
        var _top = offset.top - 5;
        var _left = offset.left - 5;
        var _width = this.$element.outerWidth() + 10;
        var _height = this.$element.outerHeight() + 10;
        this.$helper.offset({top: _top , left: _left});
        this.$helper.width(_width);
        this.$helper.height(_height);
    },
    _set_tip_position: function() {
        var self = this;
        _.each($('.oe_breathing'), function(breathing) {
            $(breathing).position({ my: "center", at: "center", of: $(breathing).prev() });
        });
    },
});

WebClient.include({
    show_application: function() {
        this._super();
        this.tip_handler = new Tip();
    }
});

var FieldStatus = core.form_widget_registry.get('statusbar');

FieldStatus.include({
    render_value: function() {
        this._super();
        this.trigger('please_reposition_tip');
    }
});

KanbanView.include({
    on_record_moved : function() {
        this._super.apply(this, arguments);
        this.trigger('kanban_reset_tip');
    }
});

kanban_common.KanbanRecord.include({
    do_action_delete : function() {
        var self = this;
        this._super.apply(this, arguments).done(function(){
            self.view.trigger('kanban_reset_tip');
        });
    }
});

ListView.include({
    reload_record : function() {
        var self = this;
        this._super.apply(this, arguments).done(function(){
            self.trigger('list_reset_tip');
        });
    }
});

});
