(function() {
    var instance = openerp;

    instance.web.Tip = instance.web.Class.extend({
        init: function() {
            var self = this;
            self.tips = [];
            self.tip_mutex = new $.Mutex();
            self.action_id = null;
            self.$overlay = null;
            self.$element = null;

            var Tips = new instance.web.Model('web.tip');
            Tips.query(['title', 'description', 'action_id', 'model', 'type', 'mode', 'trigger_selector',
                'highlight_selector', 'end_selector', 'end_event', 'placement', 'is_consumed'])
                .all().then(function(tips) {
                    self.tips = tips;
                });

            instance.web.bus.on('view_shown', this, function(view) {
                if (_.keys(view.fields_view).length === 0) {
                    view.on('view_loaded', this, function(fields_view) {
                        self.on_view(view);
                    });
                } else {
                    self.on_view(view);
                }
            });

            instance.web.bus.on('form_view_shown form_view_saved', this, function(formView) {
                self.on_form_view(formView);
            });
        },

        on_view: function(view) {
            var self = this;
            var fields_view = view.fields_view;
            if(view.ViewManager.action)
                self.action_id = view.ViewManager.action.id;
            var model = fields_view.model;

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
                    self.eval_tip(model, fields_view.type);
                });
                groups_def.done(function() {
                    self.eval_tip(model, fields_view.type);
                });
            }
            else if (fields_view.type === 'tree') {
                view.on('view_list_rendered', self, function() {
                    self.eval_tip(model, fields_view.type);
                });
            }
            else if (view.hasOwnProperty('editor')) {
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
            formView.on('view_content_has_changed', self, function() {
                self.eval_tip(model, mode, type);
            });

            if ($('.oe_chatter').length > 0) {
                instance.web.bus.on('chatter_messages_fetched', this, _.once(function () {
                    self.eval_tip(model, mode, type);
                }));
            }
            else {
                self.eval_tip(model, mode, type);
            }
        },

        eval_tip: function(model, mode, type) {
            var self = this;

            mode = (mode === "list")? "tree" : mode;

            $(self.tips).each(function(i, tip) {
                if(tip.is_consumed)
                    return;

                if(tip.action_id[0] && tip.action_id[0] !== self.action_id)
                    return;

                var tipMode = (tip.mode === "list")? "tree" : tip.mode;
                if(tip.model != model || tipMode != mode)
                    return;

                if(tip.type && tip.type !== type)
                    return;

                self.add_tip(tip);
            });
        },

        add_tip: function(tip) {
            var self = this;
            self.tip_mutex.exec(function() {
                if(!tip.is_consumed) {
                    return $.when(self.do_tip(tip));
                }
            });
        },

        do_tip: function (tip) {
            var self = this;
            var def = $.Deferred();

            // Check if tip must be triggered
            var triggers = (tip.trigger_selector)? tip.trigger_selector.split(',') : [];
            if($(tip.highlight_selector).length <= 0 || !$(tip.highlight_selector).is(":visible"))
                return def.reject();
            for(var i = 0 ; i < triggers.length ; i++) {
                if($(triggers[i]).length <= 0 || !$(triggers[i]).is(":visible"))
                    return def.reject();
            }

            // Tip to trigger !
            self.$element = $(tip.highlight_selector).filter(':visible').first();

            // Check if visible element to highlight or images in loading
            if(self.$element.height() === 0 || self.$element.width() === 0) {
                var $images = self.$element.find('img');
                if ($images.length > 0) {
                    $images.first().on('load', function(e) {
                        self.add_tip(tip);
                    });
                }
                return def.reject();
            }

            // If needed, scroll prior to displaying the tip (TODO?)
            var scroll = _.find(self.$element.parentsUntil('body'), function(el) {
                var overflow = $(el).css('overflow-y');
                return (overflow === 'auto' || overflow === 'scroll');
            });
            if(scroll)
                $(scroll).scrollTo(self.$element);

            self.$helper = $("<div>", { class: 'oe_tip_helper' });
            self.$element.after(self.$helper);
            self._set_helper_position();

            self.$overlay = $("<div>", { class: 'oe_tip_overlay' });
            $('body').append(self.$overlay);
            self.$element.addClass('oe_tip_show_element');

            // Fix the stacking context problem
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

            if(tip.title)
                $('.popover-title').prepend($cross);
            else
                $('.popover-content').prepend($cross);

            // Consume tip
            tip.end_selector = (tip.end_selector)? tip.end_selector : tip.highlight_selector;
            $(tip.end_selector).one(tip.end_event, function($ev) {
                self.end_tip(tip);
                def.resolve();
            });

            // Dismiss tip
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
            
            return def;
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
            var Tips = new instance.web.Model('web.tip');

            self.$element.popover('destroy');
            self.$overlay.remove();
            self.$helper.remove();
            self.$element.removeClass('oe_tip_show_element');
            $('.oe_tip_fix_parent').removeClass('oe_tip_fix_parent');
            $(document).off('keyup.web_tip');

            Tips.call('consume', [tip.id], {});
            tip.is_consumed = true;
        },

        reposition: function() {
            var self = this;
            if (self.tip_mutex.def.state() === 'pending') {
                self.scroll_to_tip();
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
