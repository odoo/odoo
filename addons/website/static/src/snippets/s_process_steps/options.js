/** @odoo-module **/

import options from 'web_editor.snippets.options';
import weUtils from 'web_editor.utils';
import StepsConnectorsBuilder from './utils';

options.registry.StepsConnector = options.Class.extend({

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    selectClass: function (previewMode, value, params) {
        this._super(...arguments);
        if (params.name === 'connector_type') {
            new StepsConnectorsBuilder(this.$target[0]).rebuildStepsConnectors();
            let markerEnd = '';
            if (['s_process_steps_connector_arrow', 's_process_steps_connector_curved_arrow'].includes(value)) {
                const arrowHeadEl = this.$target[0].querySelector('.s_process_steps_arrow_head');
                // The arrowhead id is set here so that they are different per snippet.
                if (!arrowHeadEl.id) {
                    arrowHeadEl.id = 's_process_steps_arrow_head' + Date.now();
                }
                markerEnd = `url(#${arrowHeadEl.id})`;
            }
            this.$target[0].querySelectorAll('.s_process_step_connector path').forEach(path => path.setAttribute('marker-end', markerEnd));
        }
    },
    /**
     * Changes arrow heads' fill color.
     *
     * @see this.selectClass for parameters
     */
    changeColor(previewMode, widgetValue, params) {
        const htmlPropColor = weUtils.getCSSVariableValue(widgetValue);
        const arrowHeadEl = this.$target[0].closest('.s_process_steps').querySelector('.s_process_steps_arrow_head');
        const color = htmlPropColor || widgetValue;
        arrowHeadEl.querySelector('path').style.fill = color;
        this.$target[0].closest('.s_process_steps').dataset.arrowColor = color;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    notify(name) {
        if (['change_column_size', 'change_container_width', 'change_columns', 'move_snippet'].includes(name)) {
            new StepsConnectorsBuilder(this.$target[0]).rebuildStepsConnectors();
        } else {
            this._super(...arguments);
        }
    },
});
