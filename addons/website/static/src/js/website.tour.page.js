(function () {
    'use strict';

    var website = openerp.website;

    website.EditorBar.include({
        start: function () {
            this.registerTour(new website.PageTour(this));
            return this._super();
        },
    });

    website.PageTour = website.Tour.extend({
        id: 'page-tutorial',
        name: "Add a page",
        init: function (editor) {
            var self = this;
            self.steps = [
                {
                    stepId: 'welcome-menu-editor',
                    orphan: true,
                    backdrop: true,
                    title: "Menu editor",
                    content: "We will show how to edit your website's menu.",
                    template: self.popover({ next: "Start Tutorial", end: "Skip It" }),
                },
                {
                    stepId: 'content-menu',
                    element: '#content-menu-button',
                    placement: 'left',
                    reflex: true,
                    title: "Edit the content",
                    content: "Click here to edit the menu.",
                },
                {
                    stepId: 'edit-entry',
                    element: 'a[data-action=edit-structure]',
                    placement: 'left',
                    title: "Edit menu",
                    content: "Click here to create a new menu entry and manage options.",
                    triggers: function () {
                        $(document).one('shown.bs.modal', function () {
                            self.moveToNextStep();
                        });
                    },
                },
                {
                    stepId: 'add-menu-entry',
                    element: 'a.js_add_menu',
                    placement: 'left',
                    title: "Add menu entry",
                    content: "Click here to create a new menu entry.",
                    triggers: function () {
                        $(document).one('shown.bs.modal', function () {
                            self.moveToNextStep();
                        });
                    },
                },
                {
                    stepId: 'enter-entry-name',
                    element: '#link-text',
                    placement: 'left',
                    title: "Choose a label",
                    content: "This label will appear in the top menu and will be visible by all your audience.\nGive a meaningful name to help your visitors. For instance, 'Photos Gallery'.",
                    template: self.popover({ next: "Continue" }),
                },
                {
                    stepId: 'enter-page-name',
                    element: '.modal .select2-container',
                    placement: 'left',
                    title: "Link your menu to a 'gallery' page",
                    content: "This page does not exist. Create it by filling the name here. For instance, 'gallery'.",
                    template: self.popover({ next: "Continue" }),
                },
                {
                    stepId: 'save-page',
                    element: '.modal-footer:last button.btn-primary',
                    placement: 'right',
                    title: "Save the page",
                    content: "Save your new page.",
                    triggers: function () {
                        $(document).one('hidden.bs.modal', function () {
                            self.moveToNextStep();
                        });
                    },
                },
                {
                    stepId: 'save-menu',
                    element: '.modal-footer button.btn-primary',
                    placement: 'right',
                    reflex: true,
                    title: "Save the menu",
                    content: "Save the menu to edit the Gallery content directly from the interface.",
                },
            ];
            return this._super();
        },
    });

}());
