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
                title:     "load web",
                onload: function () {
                    $(".collapse").addClass("in");
                },
            },
            {
                title:     "click on Settings",
                waitFor:   ".oe_view_manager_body > *:not(:empty):visible:not(.already_loaded):first",
                element:   '.oe_application_menu_placeholder a[data-menu]:contains(Settings)',
                waitNot:   ".oe_loading:visible, .oe_error_detail",
                wait: 1000
            },
            {
                title:     "click on Accounting",
                waitFor:   '.oe_application_menu_placeholder li.active a:contains(Settings)',
                element:   '.oe_secondary_menu a:visible:contains(Accounting)',
            },
            {
                title:     "click on Full accounting features",
                element:   'input[name="module_account_accountant"]:not(:checked)',
            },
            {
                title:     "click on Save",
                waitFor:   'input[name="module_account_accountant"]:checked',
                element:   'button.oe_form_button:contains(Apply)',
                onload: function () {
                    $('button.oe_form_button:contains(Apply)').addClass('already_tested');
                    $(".collapse").addClass("in");
                }
            },
            {
                title:     "click on Settings",
                element:   '.oe_application_menu_placeholder a[data-menu]:contains(Settings)',
                waitNot:   '.oe_loading:visible, button.oe_form_button:contains(Apply).already_tested',
            },
            {
                title:     "click on User",
                element:   '.oe_secondary_menu a:visible:contains(Users)',
                waitNot:   ".oe_loading:visible",
            },
            {
                title:     "click on Administrator",
                element:   '.oe_list_field_cell:contains(Administrator)',
            },
            {
                waitFor:   '.oe_breadcrumb_item:contains(Administrator)',
                waitNot:   ".oe_loading:visible",
            },
            {
                title:     "click on Edit button",
                element:   'button.oe_form_button_edit',
            },
            {
                title:     "click on Technical Features",
                element:   'td:contains(Technical Features) + td input:not(:checked):not(:disabled):visible',
            },
            {
                title:     "click on Save User",
                waitFor:   'td:contains(Technical Features) + td input:checked:not(:disabled):visible',
                element:   'button.oe_form_button_save',
                onload: function () {
                    $(".oe_view_manager_body > *:not(:empty):visible").addClass('already_tested');
                },
                onend: function () {
                    window.location.href = "/web";
                }
            },
            {
                waitNot:   'td:contains(Technical Features) + td input:checked:not(:disabled):visible',
                next:       "Check and Select next action",
            },

            {
                title:     "Click on top menu",
                element:   '.oe_application_menu_placeholder a[data-menu]:not([data-action-model="ir.actions.act_url"]):not(.already_tested):first',
                onload: function () {
                    var $menu = $(this.element);
                    console.log("Tour 'test_menu' click on: '"+$menu.text().replace(/^\s+|\s+$/g, '')+"'");
                },
                onend: function () {
                    $(this.element).addClass('already_tested');
                    $('.oe_secondary_submenu').show();
                },
                next: "Check and Select next action"
            },
            {
                title:     "Click on sub menu",
                element:   '.oe_secondary_menu a:not(.oe_menu_toggler):visible:not(.already_tested):first',
                onload: function () {
                    var $menu = $(this.element);
                    console.log("Tour 'test_menu' click on: '"+$menu.find('span:first').text().replace(/^\s+|\s+$/g, '')+"'");
                },
                onend: function () {
                    $(this.element).addClass('already_tested');
                },
                next: "Check and Select next action"
            },
            {
                title:     "Click on need action",
                element:   '.oe_secondary_menu a:not(.oe_menu_toggler) div.badge:visible:not(.already_tested):first',
                onload: function () {
                    var $menu = $(this.element);
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
                    var $menu = $(this.element);
                    console.log("Tour 'test_menu' click on switch view: '"+$menu.data('original-title')+"'");
                },
                onend: function () {
                    $(this.element).addClass('already_tested');
                },
                next: "Check and Select next action"
            },

            {
                title:    "Check and Select next action",
                waitFor:  ".oe_view_manager_body > *:not(:empty):visible:not(.already_loaded):first, .oe_form_sheet:not(.already_loaded)",
                waitNot:  ".oe_loading:visible, .oe_error_detail, .oe_form_sheetbg.already_loaded",
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
                    $(".oe_view_manager_body > *:visible:not(:empty), .oe_form_sheet").addClass("already_loaded");
                    $('.oe_view_manager_switch li.active a').addClass('already_tested');

                    $('.modal').modal('hide');
                    $(".collapse").addClass("in");

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
