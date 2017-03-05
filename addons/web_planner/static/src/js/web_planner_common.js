odoo.define('web.planner.common', function (require) {
"use strict";

var ajax = require('web.ajax');
var core = require('web.core');
var Dialog = require('web.Dialog');
var dom = require('web.dom');
var rpc = require('web.rpc');
var session = require('web.session');
var utils = require('web.utils');
var Widget = require('web.Widget');

var QWeb = core.qweb;

var _t = core._t;

var MIN_PROGRESS = 7;

var Page = core.Class.extend({
    init: function (dom, page_index) {
        this.$dom = $(dom);
        this.hide_from_menu = this.$dom.attr('hide-from-menu');
        this.hide_mark_as_done = this.$dom.attr('hide-mark-as-done');
        this.done = false;
        this.menu_item = null;
        this.title = this.$dom.find('[data-menutitle]').data('menutitle');
        this.set_page_id(this.title.replace(/\s/g, '') + page_index);
    },
    set_page_id: function (id) {
        this.id = id;
        this.$dom.attr('id', id);
    },
    get_category_name: function (category_selector) {
        return this.$dom.parents(category_selector).attr('menu-category-id');
    },
});

var PlannerDialog = Dialog.extend({
    template: "PlannerDialog",
    category_selector: "div[menu-category-id]",
    events: {
        "click li a[href^=\"#\"]:not([data-toggle=\"collapse\"])": function (e) {
            e.preventDefault();
            this._display_page($(e.currentTarget).attr("href").replace("#", ""));
        },
        "click a[href^=\"#show_enterprise\"]": function (e) {
            e.preventDefault();
            this.show_enterprise();
        },
    },
    init: function (parent, options, planner) {
        this._super.apply(this, arguments);

        this.$modal.addClass("o_planner_dialog");
        this.planner = planner;
        this.cookie_name = this.planner.planner_application + '_last_page';
        this.pages = [];
        this.menu_items = [];
        this.currently_shown_page = null;
        this.currently_active_menu_item = null,

        this.on("change:progress", this, function () {
            this.trigger('planner_progress_changed', this.get('progress'));
        });
        this.set("progress", this.planner.progress || MIN_PROGRESS);
    },
    /**
     * Fetch the planner's rendered template
     */
    willStart: function() {
        var def = rpc.query({model: 'web.planner', method: 'render'})
            .args([this.planner.view_id[0], this.planner.planner_application])
            .withContext(session.user_context)
            .exec({callback: ajax.rpc.bind(ajax)})
            .then((function (template) {
                this.$template = $(template);
            }).bind(this));

        return $.when(this._super.apply(this, arguments), def);
    },
    start: function() {
        this.$template.find(".o_planner_page").addBack(".o_planner_page").each((function (index, dom_page) {
            this.pages.push(new Page(dom_page, index));
        }).bind(this));

        this.$menu = this.$('> .o_planner_menu');
        this.$menu.html(this._render_menu());
        this.menu_items = this.$menu.find("li");
        _.each(this.pages, (function (page) {
            page.menu_item = this._find_menu_item_by_page_id(page.id);
        }).bind(this));

        this.$el.append(this.$template);

        // update the planner_data with the new inputs of the view
        var actual_vals = this._get_values();
        this.planner.data = _.defaults(this.planner.data, actual_vals);
        // set the default value
        this._set_values(this.planner.data);
        // show last opened page
        this._show_last_open_page();

        this.on("planner_progress_changed", this, this._update_title);
        this._update_title();

        this.prepare_planner_event();

        return this._super.apply(this, arguments);
    },
    prepare_planner_event: function () {}, // overriden by modules
    toggle_current_page_status: function () {
        this.currently_shown_page.done = !this.currently_shown_page.done;
        this._render_page_status(this.currently_shown_page, true);
        this._update_buttons();
        this._update_planner();
    },
    change_to_next_page: function (ev) {
        ev.preventDefault();
        this._display_page(this._get_next_page_id());
    },
    _update_title: function () {
        this.set_title(core.qweb.render("PlannerDialog.Title", {
            title: this.currently_shown_page.title,
            percent: this.get("progress")
        }));
    },
    _update_buttons: function () {
        var page = this.currently_shown_page;
        var buttons = [];
        if (!page.hide_mark_as_done) {
            buttons.push({
                text: _t("Mark As Done"),
                icon: page.done ? "fa-check-square-o" : "fa-square-o",
                classes: "o_mark_as_done btn-" + (page.done ? "default" : "primary"),
                click: this.toggle_current_page_status
            });
        }
        if (this._get_next_page_id()) {
            buttons.push({
                text: _t("Next Step"),
                icon: "fa-angle-right pull-right mt4",
                classes: "o_next_step btn-" + ((page.done || page.hide_mark_as_done) ? "primary" : "default"),
                click: this.change_to_next_page
            });
        }
        this.set_buttons(buttons);
    },
    _render_page_status: function (page, withAnim) {
        $(page.menu_item).find('span').toggleClass('fa-check', !!page.done);
        if (withAnim && page.done) { // page checked animation
            page.$dom.addClass('marked');
            _.delay(function () {
                page.$dom.removeClass('marked');
            }, 1000);
        }
    },
    _show_last_open_page: function () {
        var last_open_page = utils.get_cookie(this.cookie_name);
        if (!last_open_page) {
            last_open_page = this.planner.data.last_open_page || false;
        }

        if (last_open_page && this._find_page_by_id(last_open_page)) {
            this._display_page(last_open_page);
        } else {
            this._display_page(this.pages[0].id);
        }
    },
    _render_menu: function() {
        var orphan_pages = [];
        var menu_categories = [];
        var menu_item_page_map = {};

        // pages with no category
        _.each(this.pages, (function (page) {
            if (!page.hide_from_menu && !page.get_category_name(this.category_selector)) {
                _create_menu_item(page, orphan_pages, menu_item_page_map);
            }
        }).bind(this));

        // pages with a category
        this.$template.filter(this.category_selector).each((function (index, menu_category) {
            var $menu_category = $(menu_category);
            var menu_category_item = {
                name: $menu_category.attr('menu-category-id'),
                classes: $menu_category.attr('menu-classes'),
                menu_items: [],
            };

            _.each(this.pages, (function (page) {
                if (!page.hide_from_menu && page.get_category_name(this.category_selector) === menu_category_item.name) {
                    _create_menu_item(page, menu_category_item.menu_items, menu_item_page_map);
                }
            }).bind(this));

            menu_categories.push(menu_category_item);

            // remove the branding used to separate the pages
            this.$template = this.$template.not($menu_category);
            this.$template = this.$template.add($menu_category.contents());
        }).bind(this));

        return QWeb.render('PlannerMenu', {
            'orphan_pages': orphan_pages,
            'menu_categories': menu_categories,
            'menu_item_page_map': menu_item_page_map
        });

        function _create_menu_item(page, menu_items, menu_item_page_map) {
            var $menu_item_element = page.$dom.find('h1[data-menutitle]');
            var menu_title = $menu_item_element.data('menutitle') || $menu_item_element.text();

            menu_items.push(menu_title);
            menu_item_page_map[menu_title] = page.id;
        }
    },
    _get_next_page_id: function () {
        var currentID = this.currently_shown_page.id;
        var currentIndex = _.findIndex(this.pages, function (page) {
            return page.id === currentID;
        });
        var nextPage = this.pages[currentIndex + 1];
        return nextPage ? nextPage.id : null;
    },
    _find_page_by_id: function (id) {
        return _.find(this.pages, function (page) {
            return page.id === id;
        });
    },
    _find_menu_item_by_page_id: function (page_id) {
        return _.find(this.menu_items, function (menu_item) {
            var $menu_item = $(menu_item);
            return $($menu_item.find('a')).attr('href') === '#' + page_id;
        });
    },
    _display_page: function (page_id) {
        if (!page_id) return;

        var self = this;
        var page = this._find_page_by_id(page_id);
        if (this.currently_active_menu_item) {
            $(this.currently_active_menu_item).removeClass('active');
        }

        var menu_item = this._find_menu_item_by_page_id(page_id);
        $(menu_item).addClass('active');
        this.currently_active_menu_item = menu_item;

        if (this.currently_shown_page) {
            this.currently_shown_page.$dom.removeClass('show');
        }

        page.$dom.addClass('show');
        this.currently_shown_page = page;

        this._update_title();
        this._render_page_status(this.currently_shown_page);
        this._update_buttons();

        this.planner.data.last_open_page = page_id;
        utils.set_cookie(this.cookie_name, page_id, 8*60*60); // create cookie for 8h
        this.$el.scrollTop("0");

        this.$('textarea').each(function () {
            dom.autoresize($(this), {parent: self});
        });
    },
    // planner data functions
    _get_values: function (page) {
        // if no page_id, take the complete planner
        var base_elem = page ? page.$dom : this.$(".o_planner_page");
        var values = {};
        // get the selector for all the input and mark_button
        // only INPUT (select, textearea, input, checkbox and radio), and BUTTON (.mark_button#) are observed
        var inputs = base_elem.find("textarea[id^='input_element'], input[id^='input_element'], select[id^='input_element'], button[id^='mark_button']");
        _.each(inputs, function(elem){
            var $elem = $(elem);
            var tid = $elem.attr('id');
            if ($elem.prop("tagName") === 'BUTTON'){
                if($elem.hasClass('fa-check-square-o')){
                    values[tid] = 'marked';
                }else{
                    values[tid] = '';
                }
            }
            if ($elem.prop("tagName") === 'INPUT' || $elem.prop("tagName") === 'TEXTAREA'){
                var ttype = $elem.attr('type');
                if (ttype === 'checkbox' || ttype === 'radio'){
                    values[tid] = '';
                    if ($elem.is(':checked')){
                        values[tid] = 'checked';
                    }
                }else{
                    values[tid] = $elem.val();
                }
            }
        });

        this.pages.forEach(function(page) {
            values[page.id] = page.done;
        });
        return values;
    },
    _set_values: function(values){
        var self = this;
        _.each(values, function (val, id) {
            var $elem = self.$('[id="'+id+'"]');
            if ($elem.prop("tagName") === 'BUTTON'){
                if(val === 'marked'){
                    $elem.addClass('fa-check-square-o btn-default').removeClass('fa-square-o btn-primary');
                    self.$("li a[href=#"+$elem.data('pageid')+"] span").addClass('fa-check');
                }
            }
            if ($elem.prop("tagName") === 'INPUT' || $elem.prop("tagName") === 'TEXTAREA'){
                var ttype = $elem.attr("type");
                if (ttype  === 'checkbox' || ttype === 'radio'){
                    if (val === 'checked') {
                       $elem.attr('checked', 'checked');
                    }
                }else{
                    $elem.val(val);
                }
            }
        });

        _.each(this.pages, function (page) {
            page.done = values[page.id];
            self._render_page_status(page);
        });
    },
    _update_planner: function () {
        // update the planner.data with the inputs
        var vals = this._get_values(this.currently_shown_page);
        this.planner.data = _.extend(this.planner.data, vals);

        // re compute the progress percentage
        var total_pages = 0;
        var done_pages = 0;

        _.each(this.pages, function (page) {
            if (! page.hide_mark_as_done) {
                total_pages++;
            }
            if (page.done) {
                done_pages++;
            }
        });
        var percent = MIN_PROGRESS + parseInt(done_pages / total_pages * (100 - MIN_PROGRESS), 10);
        this.set('progress', percent);

        this.planner.progress = percent;
        // save data and progress in database
        this._save_planner_data();
    },
    _save_planner_data: function() {
        return rpc.query({model: 'web.planner', method: 'write'})
            .args([this.planner.id, {'data': JSON.stringify(this.planner.data), 'progress': this.planner.progress}])
            .exec({callback: ajax.rpc.bind(ajax)});
    },
    show_enterprise: function () {
        var buttons = [{
            text: _t("Upgrade now"),
            classes: 'btn-primary',
            close: true,
            click: function () {
                rpc.query({model: "res.users", method: "search_count"})
                    .args([[["share", "=", false]]])
                    .exec({callback: ajax.rpc.bind(ajax)})
                    .then(function (data) {
                        window.location = "https://www.odoo.com/odoo-enterprise/upgrade?utm_medium=community_upgrade&num_users=" + data;
                    });
            },
        }, {
            text: _t("Cancel"),
            close: true,
        }];
        var dialog = new Dialog(this, {
            size: 'medium',
            buttons: buttons,
            $content: $('<div>', {
                html: QWeb.render('EnterpriseUpgrade'),
            }),
            title: _t("Odoo Enterprise"),
        }).open();

        return dialog;
    },
});

var PlannerLauncher = Widget.extend({
    template: "PlannerLauncher",
    sequence: 100, // force it to be the left-most item in the systray to prevent flickering as it is not displayed in all apps
    events: {
        "click": "show_dialog"
    },
    init: function () {
        this._super.apply(this, arguments);
    },
    start: function () {
        this.$progress = this.$(".progress");
        this.$progressBar = this.$progress.find(".progress-bar");
        this.$progress.tooltip({html: true, placement: 'bottom', delay: {'show': 500}});
        this._loadPlannerDef = this._fetch_planner_data();
        return this._super.apply(this, arguments);
    },
    _fetch_planner_data: function () {},
    show_dialog: function () {
        return this._loadPlannerDef.then((function () {
            this.dialog = new PlannerDialog(this, undefined, this.planner);
            this.dialog.on("planner_progress_changed", this, this._update_parent_progress_bar);
            this.dialog.open();
        }).bind(this));
    },
    _setup_for_planner: function (planner) {
        this.planner = planner;
        this.$progress.attr('data-original-title', this.planner.tooltip_planner);
        this._update_parent_progress_bar(this.planner.progress || MIN_PROGRESS);
    },
    _update_parent_progress_bar: function (percent) {
        this.$progress.toggleClass("o_hidden", percent >= 100);
        this.$progressBar.css('width', percent + "%");
    },
});

return {
    PlannerDialog: PlannerDialog,
    PlannerLauncher: PlannerLauncher
};

});
