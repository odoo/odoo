(function () {
    'use strict';


    function openmenu () {
        setTimeout(function () {
            $(".collapse:not(.in)").addClass("in");
            $(".dropdown:not(.open)").addClass("open");
        },3000);
    }

    openerp.Tour.register({
        id:   'test_menu',
        name: "Test all menu items",
        path: '/web',
        mode: 'test',
        steps: [
            {
                title:     "begin test",
                onload: function () {
                    localStorage.setItem('active_step', 0);
                    localStorage.setItem('menu_tested', "[]");
                },
            },

            // log as admin

            {
                title:     "log on as admin",
                element:    ".oe_login_form button",
                onload: function () {
                    $('input[name="login"], input[name="password"]').val("admin");
                },
            },
            {
                title:     "load web admin",
                waitFor:   ".oe_view_manager_body",
                onload: function () {
                    localStorage.setItem('active_step', (+localStorage.getItem('active_step'))+1 );
                    openmenu();
                },
            },
            {
                title:     "click on Settings",
                element:   '.oe_application_menu_placeholder a[data-menu]:contains(Settings)',
                waitNot:   '.oe_loading:visible, button.oe_form_button:contains(Apply).already_tested',
            },

            //  add technical features to admin user

            {
                title:     "click on User form Admin",
                element:   '.oe_secondary_menu a:visible:contains(Users)',
                waitNot:   ".oe_loading:visible",
            },
            {
                title:     "click on Admin",
                element:   '.oe_list_field_cell:contains(Admin)',
            },
            {
                waitFor:   '.oe_breadcrumb_item:contains(Admin)',
                waitNot:   ".oe_loading:visible",
            },
            {
                title:     "click on Edit button",
                element:   'button.oe_form_button_edit',
            },
            {
                title:     "click on Technical Features",
                element:   'td:contains(Technical Features) + td input:not(:disabled):visible',
                onend: function () {
                    $('td:contains(Technical Features) + td input:not(:disabled):visible').attr("checked", true);
                },
            },
            {
                title:     "click on Save User",
                waitFor:   'td:contains(Technical Features) + td input:checked:not(:disabled):visible',
                element:   'button.oe_form_button_save',
            },

            //  add technical features to demo user

            {
                title:     "click on User",
                element:   '.oe_secondary_menu a:visible:contains(Users)',
                waitFor:   'td:contains(Technical Features) + td input:disabled:visible',
            },
            {
                title:     "click on Demo",
                element:   '.oe_list_field_cell:contains(Demo)',
            },
            {
                waitFor:   '.oe_breadcrumb_item:contains(Demo)',
                waitNot:   ".oe_loading:visible",
            },
            {
                title:     "click on Edit button",
                element:   'button.oe_form_button_edit',
            },
            {
                title:     "click on Technical Features",
                element:   'td:contains(Technical Features) + td input:not(:disabled):visible',
                onend: function () {
                    $('td:contains(Technical Features) + td input:not(:disabled):visible').attr("checked", true);
                    if (localStorage.getItem('active_step') === "2") {
                        $('input').attr("checked", true);
                        $('.oe_view_manager_body td:contains(Portal) + td input:visible').attr("checked", null);
                        $('.oe_view_manager_body td:contains(Public) + td input:visible').attr("checked", null);
                        $('select').each(function () {
                            $('option:last', this).attr('selected', true);
                        });
                    }
                },
            },
            {
                title:     "click on Save User",
                waitFor:   'td:contains(Technical Features) + td input:checked:not(:disabled):visible',
                element:   'button.oe_form_button_save',
                onload: function () {
                    openmenu();
                },
            },

            // log out

            {
                title:     "log out amdin",
                waitFor:   'td:contains(Technical Features) + td input:disabled:visible',
                element:   'a[data-menu="logout"]',
            },

            // log as demo

            {
                title:     "log on as demo user",
                element:    ".oe_login_form button",
                onload: function () {
                    $('input[name="login"], input[name="password"]').val("demo");
                },
            },
            {
                title:     "load web demo",
                waitFor:   ".oe_view_manager_body",
                onload: function () {
                    openmenu();
                },
                next:       "check",
            },

            // click all menu items

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
                next: "check"
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
                next: "check"
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
                next: "check"
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
                next: "check"
            },

            {
                title:    "check",
                waitNot:  "body:has("+
                              ".oe_view_manager_body > *:visible:not(:empty).already_loaded:not(.oe_searchview_drawer_container), "+
                              ".oe_form_sheetbg.already_loaded"+
                          "):not(:has(.modal))",
                wait: 100,
                onerror: function () {
                    return "Select next action";
                }
            },
            {
                title:    "add class already tested",
                waitNot:  "body.oe_wait",
                onload: function () {

                    var tested = JSON.parse(localStorage.getItem('menu_tested') || "[]");

                    $('.oe_application_menu_placeholder li.active [data-menu]').addClass('already_tested');

                    var $menu = $('.oe_secondary_menus_container li.active [data-action-model]');
                    var model = $menu.data('action-model');
                    var id = $menu.data('action-id');
                    var key = '.oe_secondary_menus_container li [data-action-model="'+model+'"][data-action-id="'+id+'"]';
                    if (tested.indexOf(key) === -1) {
                        tested.push(key);
                    }

                    var type = $('.oe_view_manager_switch li.active [data-view-type]').data('view-type');
                    var key = 'body:has(.oe_secondary_menus_container li.active [data-action-model="' + model + '"][data-action-id="' + id + '"]) '+
                        '.oe_view_manager_switch li [data-view-type="'+type+'"]';
                    if (tested.indexOf(key) === -1) {
                        tested.push(key);
                    }
                    localStorage.setItem('menu_tested', JSON.stringify(tested));


                    $(tested.join(",")).addClass('already_tested');
                    $(".oe_view_manager_body > *:visible:not(:empty), .oe_form_sheet").addClass("already_loaded");
                    $('.oe_view_manager_switch li.active a').addClass('already_tested');
                },
                wait: 250, // delay to remove wrong-positive
                onerror: function () {
                    return "Select next action";
                }
            },
            {
                title:    "Select next action",
                onload: function () {
                    if ($(".oe_error_detail").size()) {
                        console.log("Tour 'test_menu' has detected an error.");
                    }
                    if ($(".oe_dialog_warning").size()) {
                        console.log("Tour 'test_menu' has detected a warning.");
                    }

                    $('.modal').modal('hide').remove();

                    var steps = ["Click on switch view", "Click on sub menu", "Click on need action", "Click on top menu"];
                    for (var k in steps) {
                        var step = openerp.Tour.search_step(steps[k]);
                        if($(step.element).size()) {
                            return step.id;
                        }
                    }

                    openmenu();
                },
            },

            // log out and re try

            {
                title:     "log out",
                element:   'a[data-menu="logout"]',
                onend: function () {
                    if (localStorage.getItem('active_step') == "1") {
                        return "log on as admin";
                    }
                },
            },

            {
                title:     "finish",
                waitFor:   "form.oe_login_form",
                onload: function () {
                    localStorage.removeItem('active_step');
                    localStorage.removeItem('menu_tested');
                },
            }
        ]
    });

}());
