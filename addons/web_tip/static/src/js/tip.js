odoo.define('web_tip.web_tip', function (require) {
"use strict";

var core = require('web.core');
var Model = require('web.DataModel');
var WebClient = require('web.WebClient');
var formView = require('web.FormView');
var utils = require('web.utils');

var bus = core.bus;
var Class = core.Class;

var Tips = Class.extend({
    init: function() {
        var self = this;

        this.tips = [];
        this.view = null;

        var Tips = new Model('web.tip');
        Tips.query(['title', 'description', 'action_id', 'model', 'type', 'mode', 'trigger_selector',
            'highlight_selector', 'end_selector', 'end_event', 'placement', 'is_consumed'])
            .all().then(function(tips) {
                self.tips = tips;
            });

        bus.on('action', this, function(action) {
            self.on_action(action);
        });

        bus.on('view_shown', this, function(view) {
            if (_.keys(view.fields_view).length === 0) {
                view.on('view_loaded', this, function(fields_view) {
                    self.view = view;
                    self.on_view();
                });
            } else {
                self.view = view;
                self.on_view();
            }
        });
    },

    // stub
    on_action: function(action) {
        var self = this;
        var action_id = action.id;
        var model = action.res_model;
    },

    on_view: function() {
        var self = this;

        bus.on('DOM_updated', this, function() {
            var action_id = self.view.ViewManager.action ? self.view.ViewManager.action.id : null;
            var model = self.view.fields_view.model;
            var mode = self.view.fields_view.type;

            if (mode == 'form') {
                self.on_form_view(action_id, model);
            }
            else if (self.view.hasOwnProperty('editor')) {
                self.view.on('view_list_rendered', self, function() {
                    self.eval_tips(action_id, model, mode);
                });
            }
            else {
                self.eval_tips(action_id, model, mode);
            }
        });
    },

    on_form_view: function(action_id, model) {
        var self = this;
        var type = this.view.datarecord ? this.view.datarecord.type : null

        if ($('.oe_chatter').length > 0) {
            this.view.on('chatter_messages_displayed', this, function() {
                self.eval_tips(action_id, model, 'form', type);
            });
        } else {
            this.eval_tips(action_id, model, 'form', type);
        }

        this.view.on('to_edit_mode', this, function() {
            self.remove_tips();
        });
        this.view.on('to_view_mode', this, function() {
            self.eval_tips(action_id, model, 'form', type);
        });
    },

    eval_tips: function(action_id, model, mode, type) {
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
        filter.is_consumed = false;
        tips = _.where(self.tips, filter);
        // To take into account a tip without fixed model : e.g. a generic tip on the breadcrumb
        tips = tips.concat(_.where(self.tips, {mode: mode, is_consumed: false, model:false}))

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
                var t = new Tip(tip);
                t.do_tip();
            }
        });
    },

    remove_tips: function() {
        $('.oe_breathing').remove();
    },
});

var Tip = Class.extend({
    init: function(tip) {
        this.tip = tip;

        this.highlight_selector = tip.highlight_selector;
        this.end_selector = tip.end_selector ? tip.end_selector : tip.highlight_selector;
        this.triggers = tip.trigger_selector ? tip.trigger_selector.split(',') : [];
    },

    do_tip: function() {
        var self = this;

        if(!$(this.highlight_selector).length > 0 || !$(this.highlight_selector).is(":visible")) {
            return false;
        }

        for (var i = 0; i < this.triggers.length; i++) {
            if(!$(this.triggers[i]).length > 0) {
                return false;
            }
        }

        this.$element = $(this.highlight_selector).first();
        if (utils.float_is_zero(this.$element.height(), 1) || utils.float_is_zero(this.$element.width(), 1)) {
            var $images = this.$element.find('img');
            if ($images.length > 0) {
                $images.first().load(function() {
                    var t = new Tip(self.tip);
                    t.do_tip();
                    bus.trigger('image_loaded');
                });
            }
            return false;
        }

        if (!this.$element.next().hasClass('oe_breathing')) {
            this.$breathing = $("<div>", { class: 'oe_breathing' });
            this.$element.after(this.$breathing);
        } else {
            this.$breathing = this.$element.next();
        }
        this._set_breathing_position();

        this.$breathing.on('click', function(e) {
            e.stopImmediatePropagation();
            self.$breathing.addClass('oe_explode');
            self.trigger_tip();
        });

        // resize
        bus.on('resize', this, function() {
            self._set_breathing_position();
        });

        bus.on('image_loaded', this, function() {
            self._set_breathing_position();
        });

        bus.on('please_reposition_tip', this, function() {
            self._set_breathing_position();
        });

        return true;
    },

    trigger_tip: function() {
        var self = this;

        this.$helper = $("<div>", { class: 'oe_tip_helper' });
        this.$overlay = $("<div>", { class: 'oe_tip_overlay' });

        this.$element.after(this.$helper);
        this._set_helper_position();
        this.scroll_to_tip();

        var $bgElem = this.$element;
        var bgColor = $bgElem.css('background-color');
        while($bgElem.length > 0 && (bgColor === 'transparent' || bgColor === 'rgba(0, 0, 0, 0)')) {
            $bgElem = $bgElem.parent();
            bgColor = $bgElem.css('background-color');
        }
        this.$helper.css('background-color', bgColor || "white");

        $('body').append(this.$overlay);
        this.$element.addClass('oe_tip_show_element');

        // fix the stacking context problem
        _.each(this.$element.parentsUntil('body'), function(el) {
            var zIndex = $(el).css('z-index');
            var opacity = parseFloat($(el).css('opacity'));

            if (/[0-9]+/.test(zIndex) || opacity < 1) {
                $(el).addClass('oe_tip_fix_parent');
            }
        });

        this.$element.popover({
            placement: self.tip.placement,
            title: self.tip.title,
            content: self.tip.description,
            html: true,
            container: 'body',
            animation: false,
        }).popover('show');

        this.$cross = $('<button type="button" class="close oe_tip_close">&times;</button>');

        if (this.tip.title) {
            $('.popover-title').prepend(this.$cross);
        } else {
            $('.popover-content').prepend(this.$cross);
        }

        // consume tip
        $(this.end_selector).one(this.tip.end_event, function($ev) {
            self.end_tip();
        });

        // dismiss tip
        this.$cross.on('click', function($ev) {
            self.end_tip();
        });
        this.$overlay.on('click', function($ev) {
            self.end_tip();
        });
        $(document).on('keyup.web_tip', function($ev) {
            if ($ev.which === 27) { // esc
                self.end_tip();
            }
        });

        // resize
        bus.on('resize', this, function() {
            self._set_popover_position();
        });
    },

    scroll_to_tip: function(){
        var scroll = _.find(this.$element.parentsUntil('body'), function(el) {
            var overflow = $(el).css('overflow-y');
            return (overflow === 'auto' || overflow === 'scroll');
        });
        if (scroll) {
            $(scroll).scrollTo(this.$element);
        }
    },

    end_tip: function() {
        var Tips = new Model('web.tip');

        this.$element.popover('destroy');
        this.$element.removeClass('oe_tip_show_element');
        this.$breathing.remove();
        this.$helper.remove();
        this.$overlay.remove();
        this.$cross.remove();

        _.each($('.oe_tip_fix_parent'), function(el) {
            $(el).removeClass('oe_tip_fix_parent');
        });
        $(document).off('keyup.web_tip');

        Tips.call('consume', [this.tip.id], {});
        this.tip.is_consumed = true;
    },

    _set_breathing_position: function() {
        this.$breathing.position({ my: "center", at: "center", of: this.$element });
    },

    _set_helper_position: function() {
        var offset = this.$element.offset();
        var _top = offset.top - 5;
        var _left = offset.left - 5;
        var _width = this.$element.outerWidth() + 10;
        var _height = this.$element.outerHeight() + 10;

        this.$helper.offset({top: _top, left: _left});
        this.$helper.css('width', _width);
        this.$helper.css('height', _height);
    },

    _set_popover_position: function() {
        if (!this.tip.is_consumed) {
            this.$element.popover('show');
            this._set_helper_position();
            this.scroll_to_tip();

            if (this.tip.title) {
                $('.popover-title').prepend(this.$cross);
            } else {
                $('.popover-content').prepend(this.$cross);
            }
        }
    },
});

WebClient.include({
    show_application: function() {
        this._super();
        this.tips_handler = new Tips();
    }
});

formView.include({
    to_edit_mode: function() {
        this._super();
        this.trigger('to_edit_mode');
    },

    to_view_mode: function() {
        this._super();
        this.trigger('to_view_mode');
    }
});

var FieldStatus = core.form_widget_registry.get('statusbar');

FieldStatus.include({
    render_value: function() {
        this._super();
        this.trigger('please_reposition_tip');
    }
});

});
