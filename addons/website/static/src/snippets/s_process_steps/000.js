/** @odoo-module **/
import publicWidget from 'web.public.widget';

publicWidget.registry.StepSnippet = publicWidget.Widget.extend({
    selector: '.s_process_steps',
    disabledInEditableMode: false,

    /**
     * @override
     */
    willStart: function () {
        this.resizeObserver = new ResizeObserver(this._adjustConnectors.bind(this));
        this.mutationObserver = new MutationObserver((mutations) => {
            const isClassMutation = mutations.some(m => m.type === 'attributes' && m.attributeName === 'class');
            const isChildMutation = isClassMutation ? false : mutations.some(m => m.type === 'childList');
            if (isClassMutation || isChildMutation) {
                this._adjustConnectors();
                if (isChildMutation) {
                    if (this.$target[0].dataset.currentConnector === 'curved_arrow') {
                        $('.s_process_step_curved_arrow path').attr('d', 'M 0 0 Q 10 3, 20 0');
                        $('.s_process_step_curved_arrow:even path').attr('d', 'M 0 0 Q 10 -3, 20 0');
                    }
                    // We need to register added node to the observer
                    for (const {addedNodes} of mutations) {
                        for (const node of addedNodes) {
                            this.mutationObserver.observe(node, { attributes: true, attributeFilter: ['class'] });
                        }
                    }
                }
            }
        });
        const container = this.$target.find('> div > .row')[0];
        $.each($('.s_process_step'), (_, step) => {
            this.mutationObserver.observe(step, { attributes: true, attributeFilter: ['class'] });
        });
        this.mutationObserver.observe(container, { childList: true });
        this.resizeObserver.observe(container);
        this.$target.on('connectorChange', this._adjustConnectors.bind(this));
        // Add mandatory ID now because setting it in the template would lead
        // to ID duplication given that snippet thumbnails contain a copy of the template
        if ($('#arrowhead').length === 0) {
            $('#wrap .s_process_step_arrow_head').attr('id', 'arrowhead');
        }
        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    destroy: function () {
        this.$target.off('connectorChange');
        this.resizeObserver.disconnect();
        this.mutationObserver.disconnect();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Connector width is based on the distance between the two icons
     * @private
     * @returns {{arrowPosition: number, width: number}} Width of connector and position of arrow
     */
    _computeConnectorWidth($step, $next) {
        const stepIco = $step.find('i')[0];
        const nextIco = $next.find('i')[0];
        const { left: stepLeft, right: stepRight } = stepIco.getBoundingClientRect();
        const { left: nextLeft, right: nextRight } = nextIco.getBoundingClientRect();
        let width = nextLeft - stepRight;
        // In most cases arrow position is 50% - 40px (half of the icon)
        // But if the icon overflows, we need to compute the exact position
        const parentPosition = $step[0].getBoundingClientRect().right;
        let arrowPosition = stepRight + $step.width() / 2 - parentPosition;
        if (width < 40 && this.$target[0].dataset.currentConnector === 'curved_arrow') {
            width = 40;
            const stepIcoCenter = (stepLeft + stepRight) / 2;
            const nextIcoCenter = (nextLeft + nextRight) / 2;
            arrowPosition = (nextIcoCenter - stepIcoCenter) / 2 - width / 2;
        }
        return {
            arrowPosition,
            width,
        };
    },
    /**
     * Adjust connector size and position
     * If connector width is greater or equals to 70, add space between arrow and icons
     * @private
     */
    _adjustConnector($connector, connectorWidth, arrowPosition) {
        connectorWidth = connectorWidth > 0 ? connectorWidth : 0;
        const currentConnector = this.$target[0].dataset.currentConnector;
        if (currentConnector && currentConnector !== 'line' && connectorWidth - 30 >= 40) {
            connectorWidth -= 30;
            arrowPosition += 15;
        }
        $connector.attr('width', connectorWidth);
        $connector.css('left', `calc(50% + ${arrowPosition}px)`);
    },
    /**
     * @private
     */
    _adjustConnectors() {
        if (this.$target[0].dataset.currentConnector !== 'none') {
            const $steps = $('.s_process_step');
            $.each($steps, (_, step) => {
                const $step = $(step);
                const $next = $step.next('.s_process_step');
                const $connector = $step.find('.s_process_step_connector');
                // Hide connector if there is no next step or if steps are on different lines
                $connector.toggle($next.length > 0 && $next.offset().top === $step.offset().top);
                if ($next.length > 0) {
                    const { arrowPosition, width } = this._computeConnectorWidth($step, $next);
                    this._adjustConnector($connector, width, arrowPosition);
                }
            });
        }
    },
});