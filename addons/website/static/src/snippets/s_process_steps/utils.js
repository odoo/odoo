/** @odoo-module */

import {qweb} from 'web.core';

class StepsConnectorsBuilder {
    /**
     * Creates a steps connectors builder for a given steps element.
     *
     * @param {element} el steps element
     */
    constructor(el) {
        this.el = el;
    }

    /**
     * Rebuilds the steps connectors.
     * Width and position of the connectors should be updated when one of the
     * steps is modified or if they were lost after a sanitization.
     */
    rebuildStepsConnectors() {
        const steps = this.el.querySelectorAll('.s_process_step');
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
            let pathEl = connectorEl.querySelector('path');
            const pathAttr = this._getPath(width, height) || '';
            if (pathEl) {
                pathEl.setAttribute('d', pathAttr);
            } else {
                const defsSvgEl = this.el.querySelector('svg.s_process_step_svg_defs');
                connectorEl.innerHTML = qweb.render('website.s_process_steps.connectorPath', {
                    path: pathAttr,
                    arrowHeadId: this.el.classList.contains('s_process_steps_connector_arrow') ||
                        this.el.classList.contains('s_process_steps_connector_curved_arrow') ?
                        defsSvgEl.querySelector('marker').id : '',
                    color: defsSvgEl.querySelector('path').style.fill,
                });
            }
        }
    }

    // -------------------------------------------------------------------------
    // Private
    // -------------------------------------------------------------------------

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
    }
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
    }
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
    }
    /**
     * Returns the svg path based on the type of connector.
     *
     * @private
     * @param {integer} width
     * @param {integer} height
     * @returns {string}
     */
    _getPath(width, height) {
        const hHeight = height / 2;
        if (this.el.classList.contains('s_process_steps_connector_line')) {
            return `M 0 ${hHeight} L ${width} ${hHeight}`;
        } else if (this.el.classList.contains('s_process_steps_connector_arrow')) {
            return `M ${0.05 * width} ${hHeight} L ${0.95 * width - 6} ${hHeight}`;
        } else if (this.el.classList.contains('s_process_steps_connector_curved_arrow')) {
            return `M ${0.05 * width} ${hHeight * 1.2} Q ${width / 2} ${hHeight * 1.8}, ${0.95 * width - 6} ${hHeight * 1.2}`;
        }
    }
}

export default StepsConnectorsBuilder;
