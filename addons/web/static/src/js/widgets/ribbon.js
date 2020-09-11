odoo.define("web.ribbon", function (require) {
    "use strict";

    /**
     * This widget adds a ribbon on the top right side of the form
     *
     *      - You can specify the text with the title attribute.
     *      - You can specify the tooltip with the tooltip attribute.
     *      - You can specify a background color for the ribbon with the bg_color attribute
     *        using bootstrap classes :
     *        (bg-primary, bg-secondary, bg-success, bg-danger, bg-warning, bg-info,
     *        bg-light, bg-dark, bg-white)
     *
     *        If you don't specify the bg_color attribute the bg-success class will be used
     *        by default.
     */

    const widgetRegistry = require("web.widget_registry_owl");

    class RibbonComponent extends owl.Component {
        /**
         * @param {Object} props
         * @param {string} props.node.attrs.title
         * @param {string} props.node.attrs.text same as title
         * @param {string} props.node.attrs.tooltip
         * @param {string} props.node.attrs.bg_color
         */
        constructor(parent, props) {
            super(...arguments);
            this.text = props.node.attrs.title || props.node.attrs.text;
            this.tooltip = props.node.attrs.tooltip || "";
            this.className = props.node.attrs.bg_color ? props.node.attrs.bg_color : "bg-success";
            if (this.text.length > 15) {
                this.className += " o_small";
            } else if (this.text.length > 10) {
                this.className += " o_medium";
            }
        }
        async willStart() {
            const templates = await owl.utils.loadFile("/web/static/src/xml/ribbon.xml");
            if (!("web.ribbon" in this.env.qweb.templates)) {
                this.env.qweb.addTemplates(templates);
            }
            await super.willStart(...arguments);
        }
    }

    RibbonComponent.template = "web.ribbon";

    widgetRegistry.add("web_ribbon", RibbonComponent);

    return RibbonComponent;
});
