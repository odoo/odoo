odoo.define('web.SystrayMenu', function (require) {
    "use strict";

    const { ComponentAdapter } = require("web.OwlCompatibility");
    const { useRef } = owl.hooks;

    /**
     * The SystrayMenu is the class that manage the list of icons in the top right
     * of the menu bar.
     */
    class SystrayMenu extends owl.Component {
        /**
         * This widget renders the systray menu. It creates and renders widgets
         * pushed in instance.web.SystrayItems.
         */
        constructor(parent, props) {
            super(...arguments);
            this.items = [];
            this.widgets = [];
            // forcefully assign 50 as sequence to sort items to decsending order
            SystrayMenu.Items.forEach((item) => {
                if (item.prototype.sequence === undefined) {
                    item.prototype.sequence = 50;
                }
            });
            SystrayMenu.Items = _.sortBy(SystrayMenu.Items, function (item) {
                return item.prototype.sequence * -1;
            });
            this.SystrayItems = SystrayMenu.Items;
            this.refs = [];
            this.SystrayItems.forEach((item, index) => {
                this.refs.push(useRef(`systrayItem${index}`));
            });
        }
        /**
         * Instanciate the items and add the instanciated items
         */
        async mounted() {
            await super.mounted(...arguments);
            // set systray items into this.widgets
            this.refs.forEach((component) => {
                this.widgets.push(component.comp.widget);
            });
        }
    }

    SystrayMenu.template = "Systray";
    SystrayMenu.components = { ComponentAdapter };
    SystrayMenu.Items = [];

    return SystrayMenu;
});

