(function () {
    'use strict';

    openerp.Tour.register({
        id:   'choose_a_version',
        name: "Try to choose a version",
        path: '/',
        mode: 'test',
        steps: [
            //First 
            // {
            //     title:     "We begin the first step",
            // },
            // {
            //     title:     "Click on Edit",
            //     waitFor:   'button[data-action="edit"]:contains("Edit")',
            //     element:   'button[data-action="edit"]:contains("Edit")',
            // },
            // {
            //     title:     'Click on discard',
            //     waitFor:   'button[data-action="save"]:contains("Save")',
            //     element:   'a[data-action="cancel"]:contains("Discard")',
            // },
            // {
            //     title:     'Confirm Discard',
            //     element:   '.modal button[type="button"]:contains("Discard")',
            // },
            // {
            //     title:     'Finish',
            //     waitFor:   'button[data-action="edit"]:contains("Edit")',
            // },

            //Second

            {
                title:     "We begin the second step",
            },

            {
                title:     "Click on Version",
                element:   'a[id="version-menu-button"]:contains("Version"):first',
            },
            {
                title:     "Click on New version",
                element:   'a[data-action="create_snapshot"]:contains("New Version"):first',
            },

            {
                title:     "Give a version name",
                waitFor:   '.modal button[type="button"]:contains("Continue")',
                element:   '.modal input[type="text"]',
                sampleText: 'Test',
            },

            {
                title:     "Validate the version name",
                element:   '.modal button[type="button"]:contains("Continue")',
            },


            {
                title:     "Confirm",
                waitNot:   '.modal button[type="button"]:contains("Continue")',
                element:   '.modal button[type="button"]:contains("Ok")',
            },

            {
                title:     "You are on version Test",
                waitNot:   '.modal button[type="button"]:contains("Ok")',
            },

            {
                title:     "Click on Edit",
                waitFor:   'button[data-action="edit"]:contains("Edit")',
                element:   'button[data-action="edit"]:contains("Edit")',
            },

            {
                element:   'button[data-action=snippet]',
                placement: 'bottom',
                title:     "Insert building blocks",
                
            },
            {
                snippet:   '#snippet_structure .oe_snippet:first',
                placement: 'bottom',
                title:     "Drag & Drop a Banner",
            },
            {
                waitFor:   '.oe_overlay_options .oe_options:visible',
                element:   '#wrap .carousel:first div.carousel-content',
                placement: 'top',
                title:     "Customize banner's text",
                sampleText: 'Here, a customized text',
            },
            {
                waitNot:   '#wrap .carousel:first div.carousel-content:has(h2:'+
                    'containsExact('+'Your Banner Title'+')):has(h3:'+
                    'containsExact('+'Click to customize this text'+'))',
                element:   '.oe_snippet_parent:visible',
                placement: 'bottom',
                title:     "Get banner properties",
            },
            {
                element:   '.oe_overlay_options .oe_options:visible',
                placement: 'left',
                title:     "Customize the banner",
            },
            {
                waitNot:   '.popover.tour',
                element:   'button[data-action=snippet]',
                placement: 'bottom',
                title:     "Add Another Block",
            },
            {
                snippet:   '#snippet_structure .oe_snippet:eq(6)',
                placement: 'bottom',
                title:     "Drag & Drop This Block",
            },
            {
                waitFor:   '.oe_overlay_options .oe_options:visible',
                element:   'button[data-action=save]',
                placement: 'right',
                title:     "Save your modifications",
            },
            {
                waitFor:   'button[data-action=save]:not(:visible)',
                title:     "Good Job!",
            },



            // {
            //     title:     'Click on discard',
            //     waitFor:   'button[data-action="save"]:contains("Save")',
            //     element:   'a[data-action="cancel"]:contains("Discard")',
            // },
            // {
            //     title:     'Confirm Discard',
            //     element:   '.modal button[type="button"]:contains("Discard")',
            // },
            // {
            //     title:     'Finish',
            //     waitFor:   'button[data-action="edit"]:contains("Edit")',
            // },


            // {
            //     title:     'Click on discard',
            //     // waitNot:   'button[data-action="edit"]:contains("Edit")',
            //     element:   'button[data-action="cancel"]:contains("Discard"):first',
            // },
            // // {
            // //     title:     'Finish editing',
            // //     waitNot:   'button[data-action="save"]:contains("Save")',
            // // },
            // {
            //     title:     "Select version",
            //     element:   'a[id="version-menu-button"]:contains("Version"):first',
            // },
            // {
            //     title:     "Choose new version",
            //     element:   'a[data-action="change_snapshot"]:contains("New"):first',
            // },
            // {
            //     title:     'Wait the version',
            //     waitNot:   'a[data-action="change_snapshot"]:contains("New")',
            // },
        ]
    });

}());




