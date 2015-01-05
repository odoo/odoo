(function() {
    "use strict";
    var instance = openerp;
    var QWeb = instance.web.qweb;

    QWeb.add_template('/planner/static/src/xml/planner.xml');

    instance.web.Planner = instance.web.Menu.include({
        open_menu: function() {
            var self = this;
            this._super.apply(this, arguments);
            self.fetch_application_planner().done(function(application) {
                if (_.size(application)) { 
                    instance.web.planner_manager.prependTo(window.$('.oe_systray'));
                    var id = self.$el.find('.active').children().data("menu");
                    if (_.contains(_.keys(application), ''+id)) {
                        self.reflow(); //to handle progressbar display in case of menu overflowing
                        instance.web.planner_manager.planner_data = application[id];
                        instance.web.planner_manager.set_planner_tooltip(application[id].tooltip_planner);
                        instance.web.planner_manager.update_progress_value(application[id].progress);
                        instance.web.planner_manager.show();
                    } else {
                        instance.web.planner_manager.hide();
                    }
                }
            });
        },

        /**
            this method fetch the application planner data only once.
            @return object
        */
        fetch_application_planner: function() {
            var self = this;
            var def = $.Deferred();
            if (this.planner_bymenu) {
                def.resolve(self.planner_bymenu);
            } else {
                self.planner_bymenu = {};
                var fields = ['name','menu_id','view_id','progress','data','tooltip_planner','planner_application'];
                (new instance.web.Model('planner.planner')).query(fields).all().then(function(res) {
                    _(res).each(function(planner) {
                        self.planner_bymenu[planner.menu_id[0]] = planner;
                    });
                    def.resolve(self.planner_bymenu);
                }).fail(function() {def.reject();});
            }
            return def;
        }

    });

    /**
        this widget handles the show/hide of progress bar base on menu clicked by the users,
        fetch applications planner data from database, and instantiate the PlannerDialog.
    */
    instance.web.PlannerManager = instance.web.Widget.extend({
        template: "PlannerManager",
        events: {
            'click .oe_planner_progress': 'toggle_dialog'
        },

        init: function() {
            this.dialog = new instance.web.PlannerDialog();
            this.dialog.planner_manger = this;
        },
        start: function() {
            this.dialog.appendTo(document.body);
            return this._super.apply(this, arguments);
        },
        show: function() {
            this.$el.show();
        },
        hide: function() {
            this.$el.hide();
        },
        set_planner_tooltip: function(tooltip) {
            this.$el.find(".progress").tooltip({html: true, title: tooltip, placement: 'bottom', delay: {'show': 500}});
        },
        update_progress_value: function(progress_value) {
            this.$el.find(".progress-bar").css('width', progress_value+"%");
        },
        toggle_dialog: function() {
            this.dialog.$('#PlannerModal').modal('toggle');
        }
    });
    

    /**
        this widget handles the display of planner dialog and all the pages of planner,
        and also handles some operations like go to next page, mark step as done,
        store user's filled values into database etc...
    */
    instance.web.PlannerDialog = instance.web.Widget.extend({
        template: "PlannerDialog",
        events: {
            'show.bs.modal': 'show',
            'click .oe_planner div[id^="planner_page"] a[href^="#planner_page"]': 'next_page',
            'click .oe_planner li a[href^="#planner_page"]': 'onclick_menu',
            'click .oe_planner div[id^="planner_page"] button[data-progress^="planner_page"]': 'mark_as_done',
            'click .oe_planner .print_planner_report': 'print_planner_report',
        },

        onclick_menu: function(ev) {
            this.$el.find("#PlannerModal").scrollTop(0);
            //remove class active from other menu except current menu
            this.$el.find(".oe_planner li a[href^='#planner_page']").parent().removeClass('active');
            this.$el.find(ev.target).parent().addClass('active');
            //hide other pages
            this.$el.find(".oe_planner div[id^='planner_page']").removeClass('in');
        },
        next_page: function(ev) {
            this.$el.find("#PlannerModal").scrollTop(0);
            //find next page
            var next_button = $(ev.target).is("span") ? $(ev.target).parent() : $(ev.target);
            var next_page_id = $(next_button).attr('href');
            if (next_page_id) {
                this.$el.find(".oe_planner div[id="+$(next_button).attr('data-parent')+"]").removeClass('in');
                this.$el.find(".oe_planner li a[href^='#planner_page']").parent().removeClass('active');
                //find active menu
                this.$el.find(".oe_planner li a[href^='#planner_page'][href="+next_page_id+"]").parent().addClass('active');
            }
        },
        print_planner_report: function(ev) {
            var self = this;
            var newWindow = window.open();
            var pages = self.$el.find(".oe_planner div[id^='planner_page']").clone();
            $(pages).find('.hidden-print').remove();//remove element which we do not want to show during print
            var html = '';
            //append header to each page
            var header =  ($('<div>').append($('.oe_planner .oe_report_header').clone().addClass('show')));
            _.each(pages, function(el) {
                html += $('<div>').append($(el).prepend(header).removeClass('panel-collapse collapse').addClass('oe_planner_page').clone()).html();
            });
            var report = QWeb.render('PlannerReport', {'widget': this, 'content': html});
            newWindow.document.write(report);
            newWindow.document.close();
        },

        /**
            this method is called when user click on 'mark as done' button.
            this method call 'update_input_value' method to update the value of all input elements of
            current page and then call 'update_planner_data' method to store value of all input elements of
            current page
        */
        mark_as_done: function(ev) {
            var self = this;
            var btn = $(ev.target).is("span") ? $(ev.target).parent() : $(ev.target);
            var active_menu = self.$el.find(".oe_planner li a span[data-check="+btn.attr('data-progress')+"]");
            //find all inputs elements of current page
            var input_element = self.$el.find(".oe_planner div[id="+btn.attr('data-progress')+"] input[id^='input_element'], select[id^='input_element']");
            var next_button = self.$el.find(".oe_planner a[data-parent="+btn.attr('data-progress')+"]");
            if (!btn.hasClass('fa-check-square-o')) {
                //find menu element and marked as check
                active_menu.addClass('fa-check');
                //mark checked on button
                btn.addClass('fa-check-square-o btn-default').removeClass('fa-square-o btn-primary');
                next_button.addClass('btn-primary').removeClass('btn-default');
                self.update_input_value(input_element, true);
                self.values[btn.attr('id')] = 'checked';
                self.progress = self.progress + 1;
            } else {
                btn.removeClass('fa-check-square-o btn-default').addClass('fa fa-square-o btn-primary');
                next_button.addClass('btn-default').removeClass('btn-primary');
                active_menu.removeClass('fa-check');
                self.values[btn.attr('id')] = '';
                self.update_input_value(input_element, false);
                self.progress = self.progress - 1;
            }
            var data = JSON.stringify(self.values);
            var total_progress = parseInt((self.progress / self.btn_mark_as_done.length) * 100, 10);
            if (data) {
                //call update_planner_data to store JSON data into database
                self.update_planner_data(data, total_progress).then(function () {
                    //update inner and outer progress bar value
                    self.planner_manager.update_progress_value(total_progress);
                    self.$el.find(".progress-bar").css('width', total_progress+"%").text(total_progress+"%");
                    self.planner_data['data'] = data;
                    self.planner_data['progress'] = total_progress;
                });
            }
        },

        /**
            @param {boolean} save If set to true, store values of all input elements
            else clear the values of input elements.
        */
        update_input_value: function(input_element, save) {
            var self = this;
            _.each(input_element, function(element) {
                var $el = $(element);
                if ($el.attr('type') == 'checkbox' || $el.attr('type') == 'radio') {
                    if ($el.is(':checked') && save) {
                        self.values[$el.attr("id")] = 'checked';
                        $el.attr('checked', 'checked');
                    } else {
                        self.values[$el.attr("id")] = "";
                    }
                } else { 
                    if (save) {
                        self.values[$el.attr("id")] = $el.val();
                        //set value to input element, to get those value when printing report
                        $el.attr('value', $el.val());
                    } else {
                        self.values[$el.attr("id")] = "";
                    }
                }
            });
        },
        update_planner_data: function(data, progress_value) {
            return (new instance.web.DataSet(this, 'planner.planner'))
                .call('write', [this.planner_data.id, {'data': data, 'progress': progress_value}]);
        },
        add_footer: function() {
            var self = this;
            //find all the pages and append footer to each pages
            _.each(self.$el.find('.oe_planner div[id^="planner_page"]'), function(element) {
                var $el = $(element);
                var next_page_name = self.$el.find(".oe_planner .oe_planner_menu li a[href='#"+$el.next().attr('id')+"']").text() || ' Finished!';
                var footer_template = QWeb.render("PlannerFooter", {
                    'next_page_name': next_page_name, 
                    'next_page_id': $el.next().attr('id'),
                    'current_page_id': $el.attr('id'),
                    'start': $el.hasClass('start') ? true: false,
                    'end': $el.hasClass('end') ? true: false,
                });
                $el.append(footer_template);
            });
        },
        set_all_input_id: function() {
            var self = this;
            _.each(self.input_elements, function(element) {
                var $el = $(element);
                if ($el.attr('type') == 'checkbox' || $el.attr('type') == 'radio') {
                    self.values[$el.attr("id")] = '';
                } else {
                    self.values[$el.attr("id")] = $el.val();
                }
            });
            _.each(self.btn_mark_as_done, function(element) {
                var $el = $(element);
                self.values[$el.attr("id")] = '';
            });
        },

        /**
            this method fill the values of each input element from JSON data
            @param {object} JSON data
        */
        fill_input_data: function(data) {
            var self = this;
            var input_data = jQuery.parseJSON(data);
            if (!_.size(input_data)) {
                //when planner is launch for the first time, we need to store the id of each elements into database.
                self.set_all_input_id();
            } else {
                self.values = _.clone(input_data);
            }
            _.each(input_data, function(val, id){
                if ($('#'+id).prop("tagName") == 'BUTTON') {
                    if (val == 'checked') {
                        self.progress = self.progress + 1;
                        //find the menu,which need to checked
                        self.$el.find(".oe_planner li a span[data-check="+$('#'+id).attr('data-progress')+"]").addClass('fa-check');
                        var page_id = self.$el.find('#'+id).addClass('fa-check-square-o btn-default').removeClass('fa-square-o btn-primary').attr('data-progress');
                        self.$el.find(".oe_planner .planner_footer a[data-parent="+page_id+"]").addClass('btn-primary').removeClass('btn-default');
                    }
                } else if ($('#'+id).prop("tagName") == 'INPUT' && ($('#'+id).attr('type') == 'checkbox' || $('#'+id).attr('type') == 'radio')) {
                    if (val == 'checked') {
                        self.$el.find('#'+id).attr('checked', 'checked');
                    }
                } else {
                    //Set value using attr, to get those value while printing report
                    self.$el.find('#'+id).attr('value', val);
                }
            });
        },
        get_planner_page_template: function(template_id, planner_apps) {
            return (new instance.web.DataSet(this, 'planner.planner')).call('render', [template_id, planner_apps]);
        },
        load_page: function() {
            var self = this;
            self.planner_manager = instance.web.planner_manager;
            self.planner_data = self.planner_manager.planner_data;
            self.values = {}; // to store values and id of all input elements
            self.progress = 0;
            this.get_planner_page_template(self.planner_data.view_id[0], self.planner_data.planner_application).then(function(res) {
                self.$('.content').html(res);
                //set title in modal-header
                self.$el.find('.oe_planner_title').html(self.planner_data.name);
                //add footer to each page
                self.add_footer();
                //find all input elements having id start with 'input_element'
                self.input_elements = self.$el.find(".oe_planner input[id^='input_element'], select[id^='input_element']");
                //find 'mark as done' button to calculate the progress bar.
                self.btn_mark_as_done = self.$el.find(".oe_planner button[id^='input_element'][data-progress^='planner_page']");
                self.fill_input_data(self.planner_data.data);
                //fill inner progress bar value
                var progress_bar_val = parseInt((self.progress/self.btn_mark_as_done.length)*100, 10);
                self.$el.find(".progress-bar").css('width', progress_bar_val+"%").text(progress_bar_val+"%");
            });
        },
        show: function() {
            this.load_page();
        }

    });

    instance.web.planner_manager = new instance.web.PlannerManager();

})();
