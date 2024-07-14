/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("website_studio_new_form_page_collision_tour",
    {
        test: true,
        steps: () => [
        {
            // open studio
            trigger: '.o_main_navbar .o_web_studio_navbar_item',
            extra_trigger: '.o_home_menu_background',
        }, {
            trigger: '.o_web_studio_new_app',
        }, {
            // the next steps are here to create a new app
            trigger: '.o_web_studio_app_creator_next.is_ready',
        }, {
            // create 'webModule' app
            trigger: '.o_web_studio_app_creator_name > input',
            run: 'text webModule',
        }, {
            trigger: '.o_web_studio_app_creator_next.is_ready',
        }, {
            //name the module 'web', to check collision with already existing /web route
            trigger: '.o_web_studio_menu_creator > input',
            run: 'text web',
        }, {
            trigger: '.o_web_studio_app_creator_next.is_ready',
        }, {
            trigger: '.o_web_studio_model_configurator_next',
        }, {
            // switch to Website tab
            trigger: '.o_web_studio_menu .o_menu_sections li:contains(Website)',
            extra_trigger: '.o_web_studio_leave', /* wait to be inside studio */
            timeout: 60000, /* previous step reloads registry, etc. - could take a long time */
        }, {
            // click on 'New Form'
            // it should create /web-form instead of /web to prevent collision
            trigger: '.o_website_studio_form .o_web_studio_thumbnail',
        }, {
            trigger: 'img[alt="View form"]',
            run: () => {
                window.location.href = window.location.origin;
            }
        }, {
            trigger: '.o_frontend_to_backend_buttons',
            run: function () {
                const menuitems = Array.from(document.querySelectorAll('#top_menu a[role="menuitem"]'))
                    .map(x=> {
                        return {
                            href: x.getAttribute('href'),
                            name: x.textContent.trim()
                        }
                    });
                if (!menuitems.some(x => x.href === '/web-form' && x.name === 'web Form')) {
                    throw new Error('No /web-form menu item found');
                }
            },
        },
    ],
});
