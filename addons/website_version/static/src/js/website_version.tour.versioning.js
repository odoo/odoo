(function () {
    'use strict';

    var _t = openerp._t;

    openerp.Tour.register({
        id:   'versioning',
        name: "Tutorial versioning",
        path: '/',
        mode: 'tutorial',
        steps: [
            //1.

            {
                title:      _t("Welcome to the tutorial"),
                content:   _t("This tutorial will guide you to build a version of your home page."),
                popover:   { next: _t("Start Tutorial"), end: _t("Skip It") },
            },
            {
                title:      _t("Click on Version"),
                content:   _t("You can create a version for every page of your website."),
                popover:   { fixed: true },
                element:   'a[id="version-menu-button"]:contains("Version"):first',
            },
            {
                title:     _t("Click on New Version"),
                popover:   { fixed: true },
                element:   'a[data-action="create_snapshot"]:contains("New Version"):first',
            },
            {
                title:     _t("Give a version name"),
                content:   _t("Give a clever name to retrieve it easily."),
                popover:   { fixed: true },
                waitFor:   '.modal button[type="button"]:contains("Continue")',
                element:   '.modal input[type="text"]',
                sampleText: 'Test',
            },
            {
                title:     _t("Validate the version name"),
                popover:   { fixed: true },
                element:   '.modal button[type="button"]:contains("Continue")',
            },
            {
                title:     _t("Confirm"),
                popover:   { fixed: true },
                waitNot:   '.modal button[type="button"]:contains("Continue")',
                element:   '.modal button[type="button"]:contains("Ok")',
            },
            {
                title:     _t("You are on your new version"),
                content:   _t("All the modifications you will do, will be saved in this version."),
                waitNot:   '.modal button[type="button"]:contains("Ok")',
            },
            {
                title:     _t("Click on Edit"),
                content:   _t("Every page of your website can be modified through the <i>Edit</i> button."),
                waitFor:   'button[data-action="edit"]:contains("Edit")',
                element:   'button[data-action="edit"]:contains("Edit")',
            },
            {
                element:   'button[data-action=snippet]',
                placement: 'bottom',
                title:     _t("Insert building blocks"),
                content:   _t("Click here to insert blocks of content in the page."),
                popover:   { fixed: true },
            },
            {
                snippet:   '#snippet_structure .oe_snippet:first',
                placement: 'bottom',
                title:     _t("Drag & Drop a Banner"),
                content:   _t("Drag the Banner block and drop it in your page."),
                popover:   { fixed: true },
            },
            {
                waitFor:   '.oe_overlay_options .oe_options:visible',
                element:   '#wrap .carousel:first div.carousel-content',
                placement: 'top',
                title:     _t("Customize banner's text"),
                content:   _t("Click in the text and start editing it."),
                sampleText: 'Here, a customized text',
                popover:   { next: _t("Continue") },
            },
            {
                waitNot:   '#wrap .carousel:first div.carousel-content:has(h2:'+
                    'containsExact('+_t('Your Banner Title')+')):has(h3:'+
                    'containsExact('+_t('Click to customize this text')+'))',
                element:   '.oe_snippet_parent:visible',
                placement: 'bottom',
                title:     _t("Get banner properties"),
                content:   _t("Select the parent container to get the global options of the banner."),
                popover:   { fixed: true },
            },
            {
                element:   '.oe_overlay_options .oe_options:visible',
                placement: 'left',
                title:     _t("Customize the banner"),
                content:   _t("Customize any block through this menu. Try to change the background of the banner."),
                popover:   { next: _t("Continue") },
            },
            {
                waitNot:   '.popover.tour',
                element:   'button[data-action=snippet]',
                placement: 'bottom',
                title:     _t("Add Another Block"),
                content:   _t("Let's add another building block to your page."),
                popover:   { fixed: true },
            },
            {
                snippet:   '#snippet_structure .oe_snippet:eq(6)',
                placement: 'bottom',
                title:     _t("Drag & Drop This Block"),
                content:   _t("Drag the <em>'Features'</em> block and drop it below the banner."),
                popover:   { fixed: true },
            },
            {
                waitFor:   '.oe_overlay_options .oe_options:visible',
                element:   'button[data-action=save]',
                placement: 'right',
                title:     _t("Save your modifications"),
                content:   _t("Publish your page by clicking on the <em>'Save'</em> button."),
                popover:   { fixed: true },
            },
            {
                waitFor:   'button[data-action=save]:not(:visible)',
                title:     _t("Good Job!"),
                content:   _t("Well done, you created a version of your homepage."),
                popover:   { next: _t("Continue") },
            },

            //2.

            {
                title:     _t("Publish the version"),
                content:   _t("Now we will publish your version in production."),
                popover:   { next: _t("Start Tutorial"), end: _t("Skip It") },
            },

            {
                title:     _t("Click on Version"),
                element:   'a[id="version-menu-button"]:contains("Version"):first',
                popover:   { fixed: true },
            },

            {
                title:     _t("Click on Publish Version"),
                element:   'a[data-action="publish_version"]:contains("Publish Version"):first',
                popover:   { fixed: true },
            },

            {
                title:     _t("Confirm"),
                waitFor:   '.modal button[type="button"]:contains("Ok")',
                element:   '.modal button[type="button"]:contains("Ok")',
                popover:   { fixed: true },
            },


            //3.
            {
                title:     _t("Delete the version"),
                content:   _t("Now we will delete the version you have just published."),
                waitNot:   '.modal button[type="button"]:contains("Ok")',
                popover:   { next: _t("Start Tutorial"), end: _t("Skip It") },
            },

            {
                title:     _t("Click on Version"),
                element:   'a[id="version-menu-button"]:contains("Version"):first',
                popover:   { fixed: true },
            },

            {
                title:     _t("Delete Version Test"),
                element:   'li > a[data-action="delete_snapshot"]:last',
                popover:   { fixed: true },
            },

            {
                title:     _t("Confirm Yes"),
                waitFor:   '.modal button[type="button"]:contains("Yes")',
                element:   '.modal button[type="button"]:contains("Yes")',
                popover:   { fixed: true },
            },

            {
                title:     _t("Confirm"),
                waitFor:   '.modal button[type="button"]:contains("Ok")',
                element:   '.modal button[type="button"]:contains("Ok")',
                popover:   { fixed: true },
            },

            {
                title:     _t("Finish"),
                content:   _t("Felicitation, now you are able to edit and manage your versions."),
                waitNot:   '.modal button[type="button"]:contains("Ok")',
            },

        ]
    });

}());




