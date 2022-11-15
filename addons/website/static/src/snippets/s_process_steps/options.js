/** @odoo-module **/

import options from 'web_editor.snippets.options';
import weUtils from 'web_editor.utils';

options.registry.StepsConnector = options.Class.extend({
    /**
     * @override
     */
    start() {
        this.$target.on('content_changed.StepsConnector', () => this._reloadConnectors());
        return this._super(...arguments);
    },
    /**
     * @override
     */
    destroy() {
        this._super(...arguments);
        this.$target.off('.StepsConnector');
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    selectClass: function (previewMode, value, params) {
        this._super(...arguments);
        if (params.name === 'connector_type') {
            this._reloadConnectors();
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
        arrowHeadEl.querySelector('path').style.fill = htmlPropColor || widgetValue;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    notify(name) {
        if (['change_column_size', 'change_container_width', 'change_columns', 'move_snippet'].includes(name)) {
            this._reloadConnectors();
        } else {
            this._super(...arguments);
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Width and position of the connectors should be updated when one of the
     * steps is modified.
     *
     * @private
     */
    _reloadConnectors() {
        const possibleTypes = this._requestUserValueWidgets('connector_type')[0].getMethodsParams().optionsPossibleValues.selectClass;
        const type = possibleTypes.find(possibleType => possibleType && this.$target[0].classList.contains(possibleType)) || '';
        const steps = this.$target[0].querySelectorAll('.s_process_step');

        for (let i = 0; i < steps.length - 1; i++) {
            const connectorEl = steps[i].querySelector('.s_process_step_connector');
            const stepMainElementRect = this._getStepMainElementRect(steps[i]);
            const nextStepMainElementRect = this._getStepMainElementRect(steps[i + 1]);
            const stepSize = this._getStepColSize(steps[i]);
            const nextStepSize = this._getStepColSize(steps[i + 1]);
            const nextStepPadding = this._getStepColPadding(steps[i + 1]);

            connectorEl.style.left = `calc(50% + ${stepMainElementRect.width / 2}px)`;
            connectorEl.style.height = `${stepMainElementRect.height}px`;
            connectorEl.style.width = `calc(${100 * (stepSize / 2 + nextStepPadding + nextStepSize / 2) / stepSize}% - ${stepMainElementRect.width / 2}px - ${nextStepMainElementRect.width / 2}px)`;
            connectorEl.classList.toggle('d-none', nextStepMainElementRect.top > stepMainElementRect.bottom);
            const {height, width} = connectorEl.getBoundingClientRect();
            connectorEl.setAttribute('viewBox', `0 0 ${width} ${height}`);
            connectorEl.querySelector('path').setAttribute('d', this._getPath(type, width, height));
        }
    },
    /**
     * Returns the step's icon or content bounding rectangle.
     *
     * @private
     * @param {HTMLElement}
     * @returns {object}
     */
    _getStepMainElementRect(stepEl) {
        const iconEl = stepEl.querySelector('i');
        if (iconEl) {
            return iconEl.getBoundingClientRect();
        }
        const contentEls = stepEl.querySelectorAll('.s_process_step_content > *');
        // If there is no icon, the biggest text bloc in the content container
        // will be chosen.
        if (contentEls.length) {
            const contentRects = [...contentEls].map(contentEl => {
                const range = document.createRange();
                range.selectNodeContents(contentEl);
                return range.getBoundingClientRect();
            });
            return contentRects.reduce((previous, current) => {
                return current.width > previous.width ? current : previous;
            });
        }
        return {};
    },
    /**
     * Returns the size of the step, as a number of bootstrap lg-col.
     *
     * @private
     * @param {HTMLElement}
     * @returns {integer}
     */
    _getStepColSize(stepEl) {
        const colClass = stepEl.className.split(' ').find(cl => cl.startsWith('col-lg'));
        return parseInt(colClass[colClass.length - 1]);
    },
    /**
     * Returns the padding of the step, as a number of bootstrap lg-col.
     *
     * @private
     * @param {HTMLElement}
     * @returns {integer}
     */
    _getStepColPadding(stepEl) {
        const paddingClass = stepEl.className.split(' ').find(cl => cl.startsWith('offset-lg'));
        return paddingClass ? parseInt(paddingClass[paddingClass.length - 1]) : 0;
    },
    /**
     * Returns the svg path based on the type of connector.
     *
     * @private
     * @param {string} type
     * @param {integer} width
     * @param {integer} height
     * @returns {string}
     */
    _getPath(type, width, height) {
        const hHeight = height / 2;
        switch (type) {
            case 's_process_steps_connector_line': {
                return `M 0 ${hHeight} L ${width} ${hHeight}`;
            }
            case 's_process_steps_connector_arrow': {
                return `M ${0.05 * width} ${hHeight} L ${0.95 * width - 6} ${hHeight}`;
            }
            case 's_process_steps_connector_curved_arrow': {
                return `M ${0.05 * width} ${hHeight * 1.2} Q ${width / 2} ${hHeight * 1.8}, ${0.95 * width - 6} ${hHeight * 1.2}`;
            }
        }
        return '';
    },
});
