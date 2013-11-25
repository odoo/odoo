(function () {
    'use strict';

    var website = openerp.website;

    website.EditorBar.include({
        start: function () {
            this.registerTour(new website.AppTour(this));
            return this._super();
        },
    });

    website.AppTour = website.Tour.extend({
        id: 'app-tutorial',
        name: "Install an application",
        init: function (editor) {
            var self = this;
            self.steps = [
                {
                    stepId: 'welcome-install-app',
                    orphan: true,
                    backdrop: true,
                    title: "Install an App",
                    content: "You can intall some apps to manage your website content.",
                    template: self.popover({ next: "Start Tutorial", end: "Skip It" }),
                },
                {
                    stepId: 'customize',
                    element: '#customize-menu-button',
                    placement: 'left',
                    title: "Install an app",
                    content: "Add new apps by customizing your website.",
                    triggers: function () {
                        editor.on('rte:customize_menu_ready', self, self.moveToNextStep);
                    },
                },
                {
                    stepId: 'install-app',
                    element: '#customize-menu li:last a',
                    placement: 'left',
                    orphan: true,
                    title: "Install an app",
                    content: "Click 'Install Apps' to select and install the application you would like to manage from your website.",
                },
            ];
            return this._super();
        },
    });

}());
