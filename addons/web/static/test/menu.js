(function () {
    'use strict';

// data-action-model="ir.actions.client"
// data-action-id="117"
// data-menu="103"
// data-view-type

    openerp.Tour.register({
        id:   'test_menu',
        name: "Test all menu items",
        path: '/web?debug',
        mode: 'test',
        steps: [
            {
                title:     "Click on top menu",
                element:   '.oe_application_menu_placeholder a[data-menu]:not([data-action-model="ir.actions.act_url"]):not(.already_tested):first',
                onload: function () {
                    var $menu = $('.oe_application_menu_placeholder a[data-menu]:not([data-action-model="ir.actions.act_url"]):not(.already_tested):first');
                    console.log("Tour 'test_menu' click on: '"+$menu.text().replace(/^\s+|\s+$/g, '')+"'");
                },
                onend: function () {
                    $(this.element).addClass('already_tested');
                },
                next: "Check and Select next action"
            },
            {
                title:     "Click on sub menu",
                element:   '.oe_secondary_menu a:visible:not(.already_tested):first',
                onload: function () {
                    var $menu = $('.oe_secondary_menu a:visible:not(.already_tested):first');
                    console.log("Tour 'test_menu' click on: '"+$menu.find('span:first').text().replace(/^\s+|\s+$/g, '')+"'");
                },
                onend: function () {
                    $(this.element).addClass('already_tested');
                },
                next: "Check and Select next action"
            },
            {
                title:     "Click on need action",
                element:   '.oe_secondary_menu a div.badge:visible:not(.already_tested):first',
                onload: function () {
                    var $menu = $('.oe_secondary_menu a div.badge:visible:not(.already_tested):first');
                    console.log("Tour 'test_menu' click on need action: '"+$menu.parent().find('span:first').text().replace(/^\s+|\s+$/g, '')+"'");
                },
                onend: function () {
                    $(this.element).addClass('already_tested');
                },
                next: "Check and Select next action"
            },
            {
                title:     "Click on switch view",
                element:   '.oe_view_manager_switch li a:not(.already_tested):first',
                onload: function () {
                    var $menu = $('.oe_view_manager_switch li a:not(.already_tested):first');
                    console.log("Tour 'test_menu' click on switch view: '"+$menu.data('original-title')+"'");
                },
                onend: function () {
                    $(this.element).addClass('already_tested');
                },
                next: "Check and Select next action"
            },

            {
                title:    "Check and Select next action",
                waitFor:  ".oe_view_manager_body > *:not(:empty):visible:not(.already_loaded):first",
                waitNot:  ".oe_loading:visible, .oe_error_detail",
                onload: function () {
                    var tested = openerp.Tour.tours.test_menu.tested;

                    $('.oe_application_menu_placeholder li.active [data-menu]').addClass('already_tested');

                    var $menu = $('.oe_secondary_menus_container li.active [data-action-model]').addClass('already_tested');
                    var model = $menu.data('action-model');
                    var id = $menu.data('action-id');

                    var type = $('.oe_view_manager_switch li.active [data-view-type]').data('view-type');
                    var key = 'body:has(.oe_secondary_menus_container li.active [data-action-model="' + model + '"][data-action-id="' + id + '"]) '+
                        '.oe_view_manager_switch li [data-view-type="'+type+'"]';
                    if (tested.indexOf(key) === -1) {
                        tested.push(key);
                    }

                    $(tested.join(",")).addClass('already_tested');
                    $(".oe_view_manager_body > *:visible:not(:empty)").addClass("already_loaded");
                    $('.oe_view_manager_switch li.active a').addClass('already_tested');

                    $('.modal').modal('hide');

                    var steps = ["Click on switch view", "Click on sub menu", "Click on need action", "Click on top menu"];
                    for (var k in steps) {
                        var step = openerp.Tour.search_step(steps[k]);
                        if($(step.element).size()) {
                            return step.id;
                        }
                    }
                },
            },

            {
                title:     "finish"
            }
        ]
    });
    openerp.Tour.tours.test_menu.tested = [];

}());
