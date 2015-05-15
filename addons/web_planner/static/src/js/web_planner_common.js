odoo.define('web.planner.common', function (require) {
"use strict";

var core = require('web.core');
var Model = require('web.Model');
var Widget = require('web.Widget');
var utils = require('web.utils');

var QWeb = core.qweb;
var bus = core.bus;

/*
    Widget implementing the Modal of the planner (with all form, menu items, mark buttons, pages, ...). The content (the view_id) is fetched by
    calling the 'render' method (server side), then footer are appended to every pages (client side). Data are saved when a 'mark button' is clicked.
    Some element of the template MUST respect naming convention :
        * Input elements (select, textarea, radio, ...) MUST HAVE an 'id' as 'input_element_#####', where ##### is a string.
        * Page div MUST HAVE the class "o_planner_page" and an 'id' as 'planner_page#', where # is ideally a
          number. !!! The declaration order of the page are important. The 'id' number is NOT the sequence order.
        * Menu item MUST HAVE an href attribute containing the id of the page they are referencing.
*/
var PlannerDialog = Widget.extend({
    template: "PlannerDialog",
    events: {
        'click .o_planner div[id^="planner_page"] a[href^="#planner_page"]': 'change_page',
        'click .o_planner li a[href^="#planner_page"]': 'change_page',
        'click .o_planner div[id^="planner_page"] button[data-pageid^="planner_page"]': 'mark_as_done',
        'hidden.bs.modal': 'on_modal_hide',
        'shown.bs.modal': 'on_modal_show',
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
        return (new Model('web.planner')).call('render', [self.planner.view_id[0], self.planner.planner_application]).then(function(res) {
            self.$('.content_page').html(res);
            // add footer to each page
            self.add_pages_footer();
            // update the planner_data with the new inputs of the view
            var actual_vals = self._get_values();
            self.planner.data = _.defaults(self.planner.data, actual_vals);
            // set the default value
            self._set_values(self.planner.data);
            // show last opened page
            var last_open_page = (utils.get_cookie(self.cookie_name)) ? utils.get_cookie(self.cookie_name) : self.planner.data['last_open_page'] || false;
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
        this.$(".o_planner_progress_col").find('.o_planner_progress_counter').text(percent+"%");
    },
    add_pages_footer: function() {
        var self = this;
        //find all the pages and append footer to each pages
        _.each(self.$('.o_planner div[id^="planner_page"]'), function(element) {
            var $el = $(element);
            var next_page_name = self.$(".o_planner .o_planner_sidebar li a[href='#"+$el.next().attr('id')+"']").text() || ' Finished!';
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
        var $modal = this.$('.o_planner_dialog');
        $modal.height(winH/1.1);
        this.$('.o_planner_pages').height($modal.height() - 60);
        this.$('.o_planner_sidebar').height($modal.height() - 75);
    },
    // page switching
    change_page: function(ev) {
        ev.preventDefault();
        var page_id = $(ev.currentTarget).attr('href').replace('#', '');
        this._switch_page(page_id);
    },
    _switch_page: function(page_id) {
        this.$(".o_planner li a[href^='#planner_page']").parent().removeClass('active');
        this.$(".o_planner li a[href=#"+page_id+"]").parent().addClass('active');
        this.$(".o_planner div[id^='planner_page']").removeClass('show');
        this.$(".o_planner div[id="+page_id+"]").addClass('show');
        this.$(".o_planner .o_planner_pages").scrollTop("0");
        this.planner.data['last_open_page'] = page_id;
        utils.set_cookie(this.cookie_name, page_id, 8*60*60); // create cookie for 8h
    },
    // planner data functions
    _get_values: function(page_id){
        // if no page_id, take the complete planner
        var base_elem = page_id ? this.$(".o_planner div[id="+page_id+"]") : this.$(".o_planner div[id^='planner_page']");
        var values = {};
        // get the selector for all the input and mark_button
        // only INPUT (select, textearea, input, checkbox and radio), and BUTTON (.mark_button#) are observed
        var inputs = base_elem.find("textarea[id^='input_element'], input[id^='input_element'], select[id^='input_element'], button[id^='mark_button']");
        _.each(inputs, function(elem){
            var $elem = $(elem);
            var tid = $elem.attr('id');
            if ($elem.prop("tagName") == 'BUTTON'){
                if($elem.hasClass('fa-check-square-o')){
                    values[tid] = 'marked';
                }else{
                    values[tid] = '';
                }
            }
            if ($elem.prop("tagName") == 'INPUT' || $elem.prop("tagName") == 'TEXTAREA'){
                var ttype = $elem.attr('type');
                if (ttype == 'checkbox' || ttype == 'radio'){
                    values[tid] = '';
                    if ($elem.is(':checked')){
                        values[tid] = 'checked';
                    }
                }else{
                    values[tid] = $elem.val();
                }
            }
        });
        return values;
    },
    _set_values: function(values){
        var self = this;
        _.each(values, function(val, id){
            var $elem = self.$('#'+id);
            if ($elem.prop("tagName") == 'BUTTON'){
                if(val == 'marked'){
                    $elem.addClass('fa-check-square-o btn-default').removeClass('fa-square-o btn-primary');
                    self.$(".o_planner li a[href=#"+$elem.data('pageid')+"] span").addClass('fa-check');
                }
            }
            if ($elem.prop("tagName") == 'INPUT' || $elem.prop("tagName") == 'TEXTAREA'){
                var ttype = $elem.attr("type");
                if (ttype  == 'checkbox' || ttype == 'radio'){
                    if (val == 'checked') {
                       $elem.attr('checked', 'checked');
                    }
                }else{
                    $elem.val(val);
                }
            }
        });
    },
    update_planner: function(page_id){
        // update the planner.data with the inputs
        var vals = this._get_values(page_id);
        this.planner.data = _.extend(this.planner.data, vals);
        // re compute the progress percentage
        var mark_btn = this.$(".o_planner button[id^='mark_button']");
        var marked_btn = this.$(".o_planner button[id^='mark_button'].fa-check-square-o");
        var percent = parseInt((marked_btn.length+1) / (mark_btn.length+1) * 100);
        this.set('progress', percent);
        this.planner.progress = percent;
        // save data and progress in database
        this._save_planner_data();
    },
    _save_planner_data: function() {
        return (new Model('web.planner')).call('write', [this.planner.id, {'data': JSON.stringify(this.planner.data), 'progress': this.planner.progress}]);
    },
    // user actions
    mark_as_done: function(ev) {
        var self = this;
        var btn = $(ev.currentTarget);
        var page_id = btn.attr('data-pageid');
        var active_menu = self.$(".o_planner li a[href=#"+page_id+"] span");
        var active_page = self.$(".o_planner div[id^='planner_page'].o_planner_page.show");

        var next_button = self.$(".o_planner a[data-parent="+page_id+"]");
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
    on_modal_show : function(e) {
        bus.on('action', this, _.bind(this.on_webclient_action, this));
        $(window).on("unload", this, _.bind(this.on_webclient_action, this)); // bind the action of quitting the window
    },
    on_modal_hide : function(e) {
        bus.off('action', this, _.bind(this.on_webclient_action, this));
        $(window).off("unload", this, _.bind(this.on_webclient_action, this)); // unbind the action of quitting the window
        this.update_planner(); // explicit call to save data
    },
    on_webclient_action: function(e) {
        this.$('#PlannerModal').modal('hide');
    },
});
return {
    PlannerDialog: PlannerDialog,
};

});

