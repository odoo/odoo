/** @odoo-module **/
import options from 'web_editor.snippets.options';

options.registry.ConnectorChoice = options.Class.extend({

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Change connector type
     */
    changeConnector: function (previewMode, widgetValue, params) {
        this.$target[0].dataset.currentConnector = widgetValue;
        // Lets notify the snippet that a connector has change in order
        // to adjust connector width
        this.$target.trigger('connectorChange');
        this.$target.find('.s_process_step_connector').toggleClass('s_process_step_curved_arrow', widgetValue === 'curved_arrow');
        const arrowPath = widgetValue === 'curved_arrow' ? 'M 0 0 Q 10 2, 20 0' : 'M 0 0 L 20 0';
        const isArrow = widgetValue.includes('arrow');
        this.$target.find('.s_process_step_connector path').attr({
            d: arrowPath,
            'stroke-width': isArrow ? 2 : 1,
            'marker-end': isArrow ? 'url(#arrowhead)' : '',
        }).toggle(widgetValue !== 'none');
        $('.s_process_step_curved_arrow:even path').attr('d', 'M 0 0 Q 10 -2, 20 0');
    },
    /**
     * Change arrow heads' fill color according to stroke color
     */
    changeColor: function (previewMode, widgetValue, params) {
        const color = this.$target.closest('.s_process_step_connector path').css('stroke');
        $('.s_process_step_arrow_head path').css('fill', color);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeWidgetState: function (methodName, params) {
        switch (methodName) {
            case "changeConnector":
                return this.$target[0].dataset.currentConnector;
        }
        return this._super(...arguments);
    },
});