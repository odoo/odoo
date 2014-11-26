(function() {

    var instance = openerp;

    instance.web.Tip = instance.web.Class.extend({
        init: function() {
            var self = this;
            self.tips = [];
            self.tip_mutex = new $.Mutex();
            self.$overlay = null;
            self.$element = null;

            var Tips = new instance.web.Model('web.tip');
            Tips.query(['title', 'description', 'action_id', 'model', 'type', 'mode', 'trigger_selector',
                'highlight_selector', 'end_selector', 'end_event', 'placement', 'is_consumed'])
                .all().then(function(tips) {
                    self.tips = tips;
                })
            ;

            instance.web.bus.on('action', this, function(action) {
                self.on_action(action);
            });

            instance.web.bus.on('view_shown', this, function(view) {
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

            instance.web.bus.on('view_switch_mode', this, function(viewManager, mode) {
                self.on_switch(viewManager, mode);
            });

            instance.web.bus.on('form_view_shown', this, function(formView) {
                self.on_form_view(formView);
            });

            instance.web.bus.on('form_view_saved', this, function(formView) {
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
                dataset_def.done(function(length) {
                    self.eval_tip(action_id, model, fields_view.type);
                });
                groups_def.done(function() {
                    self.eval_tip(action_id, model, fields_view.type);
                });
            } else if (fields_view.type === 'tree') {
                view.on('view_list_rendered', self, function() {
                    self.eval_tip(action_id, model, fields_view.type);
                });
            } else if (view.hasOwnProperty('editor')) {
                view.on('view_list_rendered', self, function() {
                    self.reposition();
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
                instance.web.bus.on('chatter_messages_fetched', this, _.once(function () {
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
                    self.add_tip(tip);
                }
            });
        },


        add_tip: function(tip) {
            var self = this;
            self.tip_mutex.exec(function() {
                if (!tip.is_consumed) {
                    return $.when(self.do_tip(tip));
                }
            });
        },

        do_tip: function (tip) {
            var self = this;
            var def = $.Deferred();
            var Tips = new instance.web.Model('web.tip');
            var highlight_selector = tip.highlight_selector;
            var triggers = tip.trigger_selector ? tip.trigger_selector.split(',') : [];
            var trigger_tip = true;

            if(!$(highlight_selector).length > 0) {
                return def.reject();
            }
            for (var i = 0; i < triggers.length; i++) {
                if(!$(triggers[i]).length > 0) {
                    trigger_tip = false;
                }
            }

            if (trigger_tip) {
                self.$element = $(highlight_selector).first();
                if (self.$element.height() === 0 || self.$element.width() === 0) {
                    var $images = self.$element.find('img');
                    if ($images.length > 0) {
                        $images.first().load(function() {
                            self.add_tip(tip);
                        });
                    }
                    return def.reject();
                }

                // if needed, scroll prior to displaying the tip
                var scroll = _.find(self.$element.parentsUntil('body'), function(el) {
                    var overflow = $(el).css('overflow-y');
                    return (overflow === 'auto' || overflow === 'scroll');
                });
                if (scroll) {
                    $(scroll).scrollTo(self.$element);
                }

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
                }).popover("show");

                var $cross = $('<button type="button" class="close">&times;</button>');
                $cross.addClass('oe_tip_close');

                if (tip.title) {
                    $('.popover-title').prepend($cross);
                } else {
                    $('.popover-content').prepend($cross);
                }

                // consume tip
                tip.end_selector = tip.end_selector ? tip.end_selector : tip.highlight_selector;
                $(tip.end_selector).one(tip.end_event, function($ev) {
                    self.end_tip(tip);
                    def.resolve();
                });

                // dismiss tip
                $cross.on('click', function($ev) {
                    self.end_tip(tip);
                    def.resolve();
                });
                self.$overlay.on('click', function($ev) {
                    self.end_tip(tip);
                    def.resolve();
                });
                $(document).on('keyup.web_tip', function($ev) {
                    if ($ev.which === 27) { // esc
                        self.end_tip(tip);
                        def.resolve();
                    }
                });

                // resize
                instance.web.bus.on('resize', this, function() {
                    self.reposition();
                });
            } else {
               def.reject();
            }
            return def;
        },

        end_tip: function(tip) {
            var self = this;
            var Tips = new instance.web.Model('web.tip');
            $('#' + self.$element.attr('aria-describedby')).remove();
            self.$overlay.remove();
            self.$helper.remove();
            self.$element.removeClass('oe_tip_show_element');
            _.each($('.oe_tip_fix_parent'), function(el) {
                $(el).removeClass('oe_tip_fix_parent');
            });
            $(document).off('keyup.web_tip');
            Tips.call('consume', [tip.id], {});
            tip.is_consumed = true;
        },

        reposition: function() {
            var self = this;
            if (self.tip_mutex.def.state() === 'pending') {
                self._set_helper_position();
                self.$element.popover('show');
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
        }
    });

    instance.web.WebClient = instance.web.WebClient.extend({
        show_application: function() {
            this._super();
            this.tip_handler = new instance.web.Tip();
        }
    });

    instance.web.form.FieldStatus = instance.web.form.FieldStatus.extend({
        render_value: function() {
            this._super();
            instance.webclient.tip_handler.reposition();
        }
    });
})();
