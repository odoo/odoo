/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import {NavBar} from '@web/webclient/navbar/navbar';
import {useEffect, useRef} from '@odoo/owl';
import { patch } from "@web/core/utils/patch";
import { renderToString } from "@web/core/utils/render";

// todo: 处理为固定在某处的信息，一直显示last menu xmlid,然后有2个btn，一个copy xmlid，一个是关闭
patch(NavBar.components.Dropdown.prototype, {
    setup() {
        super.setup();
        useEffect(() => this.addDebugTooltip());
    },

    addDebugTooltip() {
        let is_asset = browser.location.search.includes('?debug=assets');
        if (is_asset && this.props && this.props.payload) {
            const debugData = {
                id: this.props.payload.id,
                title: this.props.payload.name,
                xmlid: this.props.payload.xmlid,
                sequence: this.props.payload.sequence,
            };

            const dropdownToggle = document.querySelectorAll(`.dropdown-toggle[data-menu-xmlid="${debugData.xmlid}"], .dropdown-toggle[data-section="${debugData.id}"]`);

            if (dropdownToggle && dropdownToggle.length > 0) {
                const el = dropdownToggle[0];
                el.removeAttribute('title');
                const debugTooltip = {
                    template: '<div class="tooltip tooltip-field-info" role="tooltip"><div class="arrow"></div><div class="tooltip-inner"></div></div>',
                    title: renderToString('Menu.tooltip', debugData),
                };
                bindCustomTooltip(el, debugTooltip.title);
            }
        }
    },
});

NavBar.components.Dropdown.props.payload = {
    type: Object,
    optional: true,
};

patch(NavBar.components.DropdownItem.prototype, {
    setup() {
        super.setup();
        useEffect(() => this.addDebugTooltip());
    },
    addDebugTooltip() {
        let is_asset = browser.location.search.includes('?debug=assets');
        if (is_asset) {
            let menuDebugData = this.getDebugData();
            if (!menuDebugData) {
                return;
            }
            const menuItems = document.querySelectorAll(`.dropdown-item[data-menu-xmlid="${menuDebugData.xmlid}"], .dropdown-item[data-section="${menuDebugData.id}"]`);
            menuItems.forEach(item => {
                item.removeAttribute('title');
                const debugTooltip = this.getDebugTooltip(menuDebugData);
                bindCustomTooltip(item, debugTooltip.title);
            });
        }
    },
    getDebugData() {
        if (!this.props.payload) {
            return null;
        }
        return {
            id: this.props.payload.id,
            title: this.props.payload.name,
            xmlid: this.props.payload.xmlid,
            sequence: this.props.payload.sequence,
        }
    },
    getDebugTooltip(debugData) {
        return {
            template: '<div class="tooltip tooltip-field-info" role="tooltip"><div class="arrow"></div><div class="tooltip-inner"></div></div>',
            title: renderToString('Menu.tooltip', debugData),
        };
    },
})

NavBar.components.DropdownItem.props.payload = {
    type: Object,
    optional: true,
};

function bindCustomTooltip(element, tooltipHtml) {
    element.onmouseenter = null;
    element.onmouseleave = null;
    element.onmouseenter = function (e) {
        let tooltip = document.createElement('div');
        tooltip.className = 'custom-tooltip';
        tooltip.innerHTML = tooltipHtml;
        document.body.appendChild(tooltip);

        const rect = element.getBoundingClientRect();
        const tooltipRect = tooltip.getBoundingClientRect();

        tooltip.style.left = (rect.right + window.scrollX + 8) + 'px';
        tooltip.style.top = (rect.top + window.scrollY + (rect.height - tooltipRect.height) / 2 + 12) + 'px';
    };
    element.onmouseleave = function () {
        const tooltip = document.querySelector('.custom-tooltip');
        if (tooltip) tooltip.remove();
    };
}
