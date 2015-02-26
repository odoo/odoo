(function() {

    "use strict";

    var instance = openerp;
    var QWeb = instance.web.qweb;
    instance.planner = {};

    instance.planner.PlannerLauncher = instance.web.Widget.extend({
        template: "PlannerLauncher",
        events: {
            'click .oe_planner_progress': 'toggle_dialog'
        },
        init: function(parent) {
            this._super(parent);
            this.planner_by_menu = {};
            this.webclient = parent.getParent();
            this.need_reflow = false;
        },
        start: function() {
            var self = this;
            self._super();

            self.webclient.menu.on("open_menu", self, self.on_menu_clicked);
            self.$el.hide();  // hidden by default
            return self.fetch_application_planner().done(function(apps) {
                self.planner_apps = apps;
                return apps;
            });
        },
        fetch_application_planner: function() {
            var self = this;
            var def = $.Deferred();
            if (!_.isEmpty(this.planner_by_menu)) {
                def.resolve(self.planner_by_menu);
            }else{
                (new instance.web.Model('planner.planner')).query().all().then(function(res) {
                    _.each(res, function(planner){
                        self.planner_by_menu[planner.menu_id[0]] = planner;
                        self.planner_by_menu[planner.menu_id[0]].data = jQuery.parseJSON(self.planner_by_menu[planner.menu_id[0]].data) || {};
                    });
                    def.resolve(self.planner_by_menu);
                }).fail(function() {def.reject();});
            }
            return def;
        },
        on_menu_clicked: function(id, $clicked_menu) {
            var menu_id = $clicked_menu.parents('.oe_secondary_menu').data('menu-parent') || 0; // find top menu id
            if (_.contains(_.keys(this.planner_apps), menu_id.toString())) {
                this.$el.show();
                this.setup(this.planner_apps[menu_id]);
                this.need_reflow = true;
            } else {
                if (this.$el.is(":visible")) {
                    this.$el.hide();
                    this.need_reflow = true;
                }
            }
            if (this.need_reflow) {
                this.webclient.menu.reflow();
                this.need_reflow = false;
            }
        },
        setup: function(planner){
            var self = this;
            this.planner = planner;
            this.dialog = new instance.planner.PlannerDialog(this, planner);
            this.$(".oe_planner_progress").tooltip({html: true, title: this.planner.tooltip_planner, placement: 'bottom', delay: {'show': 500}});
            this.dialog.on("planner_progress_changed", this, function(percent){
                self.update_parent_progress_bar(percent);
            });
            this.dialog.appendTo(document.body);
        },
        // event
        update_parent_progress_bar: function(percent) {
            this.$(".progress-bar").css('width', percent+"%");
        },
        toggle_dialog: function() {
            this.dialog.$('#PlannerModal').modal('toggle');
        }
    });


    /*
        Widget implementing the Modal of the planner (with all form, menu items, mark buttons, pages, ...). The content (the view_id) is fetched by
        calling the 'render' method (server side), then footer are appended to every pages (client side). Data are saved when a 'mark button' is clicked.
        Some element of the template MUST respect naming convention :
            * Input elements (select, textarea, radio, ...) MUST HAVE an 'id' as 'input_element_#####', where ##### is a string.
            * Page div MUST HAVE the class "planner-page" and an 'id' as 'planner_page#', where # is ideally a
              number. !!! The declaration order of the page are important. The 'id' number is NOT the sequence order.
            * Menu item MUST HAVE an href attribute containing the id of the page they are referencing.
    */
    instance.planner.PlannerDialog = instance.web.Widget.extend({
        template: "PlannerDialog",
        events: {
            'click .oe_planner div[id^="planner_page"] a[href^="#planner_page"]': 'change_page',
            'click .oe_planner li a[href^="#planner_page"]': 'change_page',
            'click .oe_planner div[id^="planner_page"] button[data-pageid^="planner_page"]': 'mark_as_done',
        },
        init: function(parent, planner) {
            this._super(parent);
            this.planner_launcher = parent;
            this.planner = planner;
            this.cookie_name = this.planner['planner_application'] + '_last_page';
            this.set('progress', 0);
        },
        start: function() {
            var self = this;
            this._super.apply(this, arguments);
            this._setup_view().then(function(){
                self.prepare_planner_event();
            });
        },
        // This method should be overridden in other planners to bind their custom events, once the view is loaded.
        prepare_planner_event: function() {
            var self = this;
            self.on('change:progress', self, function(){
                self.trigger('planner_progress_changed', self.get('progress'));
            });
            this.on('planner_progress_changed', this, this.update_ui_progress_bar);
            this.set('progress', this.planner.progress); // init progress to trigger ui update

            $(window).on('resize', function() {
                self.resize_dialog();
            });
        },
        // ui
        _setup_view: function(){
            var self = this;
            return (new instance.web.Model('planner.planner')).call('render', [self.planner.view_id[0], self.planner.planner_application]).then(function(res) {
                self.$('.content_page').html(res);
                // add footer to each page
                self.add_pages_footer();
                // update the planner_data with the new inputs of the view
                var actual_vals = self._get_values();
                self.planner.data = _.defaults(self.planner.data, actual_vals);
                // set the default value
                self._set_values(self.planner.data);
                // show last opened page
                var last_open_page = (openerp.session.get_cookie(self.cookie_name)) ? openerp.session.get_cookie(self.cookie_name) : self.planner.data['last_open_page'] || false;
                if (last_open_page) {
                    self._switch_page(last_open_page);
                }
                // Call resize function at the beginning
                self.resize_dialog();
                self.$el.on('keyup', "textarea", function() {
                    if (this.scrollHeight != this.clientHeight) {
                        this.style.height = this.scrollHeight + "px";
                    }
                });
            });
        },
        update_ui_progress_bar: function(percent) {
            this.$(".progress-bar").css('width', percent+"%");
            this.$(".progress_col").find('span.counter').text(percent+"%");
        },
        add_pages_footer: function() {
            var self = this;
            //find all the pages and append footer to each pages
            _.each(self.$('.oe_planner div[id^="planner_page"]'), function(element) {
                var $el = $(element);
                var next_page_name = self.$(".oe_planner .side li a[href='#"+$el.next().attr('id')+"']").text() || ' Finished!';
                var footer_template = QWeb.render("PlannerFooter", {
                    'next_page_name': next_page_name,
                    'next_page_id': $el.next().attr('id'),
                    'current_page_id': $el.attr('id'),
                    'start': $el.prev().length ? false: true,
                    'end': $el.next().length ? false: true
                });
                $el.append(footer_template);
            });
        },
        resize_dialog: function() {
            var winH  = $(window).height();
            var $modal = this.$('.planner-dialog');
            $modal.height(winH/1.1);
            this.$('.pages').height($modal.height() - 60);
            this.$('.side').height($modal.height() - 75);
        },
        // page switching
        change_page: function(ev) {
            ev.preventDefault();
            var page_id = $(ev.currentTarget).attr('href').replace('#', '');
            this._switch_page(page_id);
        },
        _switch_page: function(page_id) {
            this.$(".oe_planner li a[href^='#planner_page']").parent().removeClass('active');
            this.$(".oe_planner li a[href=#"+page_id+"]").parent().addClass('active');
            this.$(".oe_planner div[id^='planner_page']").removeClass('show');
            this.$(".oe_planner div[id="+page_id+"]").addClass('show');
            this.planner.data['last_open_page'] = page_id;
            openerp.session.set_cookie(this.cookie_name, page_id, 8*60*60); // create cookie for 8h
        },
        // planner data functions
        _get_values: function(page_id){
            // if no page_id, take the complete planner
            var base_elem = page_id ? this.$el : this.$(".oe_planner div[id='planner_page"+page_id+"']");
            var values = {};
            // get the selector for all the input and mark_button
            // only INPUT (select, textearea, input, checkbox and radio), and BUTTON (.mark_button#) are observed
            var inputs = base_elem.find("textarea[id^='input_element'], input[id^='input_element'], select[id^='input_element'], button[id^='mark_button']");
            _.each(inputs, function(elem){
                elem = $(elem);
                var tid = elem.attr('id');
                if (elem.prop("tagName") == 'BUTTON'){
                    if(elem.hasClass('fa-check-square-o')){
                        values[tid] = 'marked';
                    }else{
                        values[tid] = '';
                    }
                }
                if (elem.prop("tagName") == 'INPUT' || elem.prop("tagName") == 'TEXTAREA'){
                    var ttype = elem.attr('type');
                    if (ttype == 'checkbox' || ttype == 'radio'){
                        values[tid] = '';
                        if (elem.is(':checked')){
                            values[tid] = 'checked';
                        }
                    }else{
                        values[tid] = elem.val();
                    }
                }
            });
            return values;
        },
        _set_values: function(values){
            var self = this;
            _.each(values, function(val, id){
                var elem = self.$('#'+id);
                if (elem.prop("tagName") == 'BUTTON'){
                    if(val == 'marked'){
                        elem.addClass('fa-check-square-o btn-default').removeClass('fa-square-o btn-primary');
                        self.$(".oe_planner li a[href=#"+elem.data('pageid')+"] span").addClass('fa-check');
                    }
                }
                if (elem.prop("tagName") == 'INPUT' || elem.prop("tagName") == 'TEXTAREA'){
                    var ttype = elem.attr("type");
                    if (ttype  == 'checkbox' || ttype == 'radio'){
                        if (val == 'checked') {
                           elem.attr('checked', 'checked');
                        }
                    }else{
                        elem.val(val);
                    }
                }
            });
        },
        update_planner: function(page_id){
            // update the planner.data with the inputs
            var vals = this._get_values(page_id);
            this.planner.data = _.extend(this.planner.data, vals);
            // re compute the progress percentage
            var mark_btn = this.$(".oe_planner button[id^='mark_button']");
            var marked_btn = this.$(".oe_planner button[id^='mark_button'].fa-check-square-o");
            var percent = parseInt((marked_btn.length+1) / (mark_btn.length+1) * 100);
            this.set('progress', percent);
            this.planner.progress = percent;
            // save data and progress in database
            this._save_planner_data();
        },
        _save_planner_data: function() {
            return (new instance.web.Model('planner.planner')).call('write', [this.planner.id, {'data': JSON.stringify(this.planner.data), 'progress': this.planner.progress}]);
        },
        // user actions
        mark_as_done: function(ev) {
            var self = this;
            var btn = $(ev.currentTarget);
            var page_id = btn.attr('data-pageid');
            var active_menu = self.$(".oe_planner li a[href=#"+page_id+"] span");
            var active_page = self.$(".oe_planner div[id^='planner_page'].planner-page.show");

            var next_button = self.$(".oe_planner a[data-parent="+page_id+"]");
            if (!btn.hasClass('fa-check-square-o')) {
                active_menu.addClass('fa-check');
                btn.addClass('fa-check-square-o btn-default').removeClass('fa-square-o btn-primary');
                next_button.addClass('btn-primary').removeClass('btn-default');
                // page checked animation
                active_page.addClass('marked');
                setTimeout(function() { active_page.removeClass('marked'); }, 1000);
            } else {
                btn.removeClass('fa-check-square-o btn-default').addClass('fa-square-o btn-primary');
                next_button.addClass('btn-default').removeClass('btn-primary');
                active_menu.removeClass('fa-check');
            }
            self.update_planner(page_id);
        },
    });

    // add planner launcher to the systray
    // if it is empty, it won't be display. Then, each time a top menu is clicked
    // a planner will be given to the launcher. The launcher will appears if the
    // given planner is not null.
    openerp.web.SystrayItems.push(instance.planner.PlannerLauncher);

})();
