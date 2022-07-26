/** @odoo-module */

import {qweb} from 'web.core';
import publicWidget from 'web.public.widget';
import StepsConnectorsBuilder from './utils';

const ProcessStepsWidget = publicWidget.Widget.extend({
    selector: '.s_process_steps',
    xmlDependencies: ['/website/static/src/snippets/s_process_steps/000.xml'],

    /**
     * @override
     */
    start() {
        if (!this.el.querySelector('svg.s_process_step_svg_defs defs')) {
            // The inline SVGs inside the snippet are empty. This is probably due
            // the sanitization of a field during the save, like in a product
            // description field.
            // In such cases, reconstruct the steps connectors.
            this.el.querySelector('svg.s_process_step_svg_defs').innerHTML = qweb.render(
                'website.s_process_steps.defs', {
                    color: this.el.dataset.arrowColor,
                    id: 's_process_steps_arrow_head' + Date.now(),
                }
            );
            new StepsConnectorsBuilder(this.el).rebuildStepsConnectors();
        }
        return this._super(...arguments);
    },
});

publicWidget.registry.processSteps = ProcessStepsWidget;

export default ProcessStepsWidget;
