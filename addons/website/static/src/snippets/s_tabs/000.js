/** @odoo-module */

import publicWidget from 'web.public.widget';
import { closestElement } from '@web_editor/js/editor/odoo-editor/src/OdooEditor';

const TabsWidget = publicWidget.Widget.extend({
    selector: '.s_tabs',
    disabledInEditableMode: false,

    /**
     * @override
     */
    async start() {
        const _onKeyDownPreventTab = (ev) => {
            if (this.editableMode && ev.key === "Tab") {
                const closestDivEl = closestElement(this.el.ownerDocument.getSelection().anchorNode, "div");
                if (closestDivEl && closestDivEl.classList.contains("s_tabs_nav")) {
                    ev.stopPropagation();
                    ev.preventDefault();
                }
            }
        }
        if (this.editableMode) {
            this.el.ownerDocument.addEventListener("keydown", _onKeyDownPreventTab, true);
        }
        return this._super(...arguments);
    },
});

publicWidget.registry.tabs = TabsWidget;

export default TabsWidget;
