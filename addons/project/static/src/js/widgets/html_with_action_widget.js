/** @odoo-module **/

import { device } from 'web.config';
import { bus } from 'web.core';
import fieldRegistry from 'web.field_registry';
import FieldHtml from 'web_editor.field.html';

export const FieldHtmlWithAction = FieldHtml.extend({
    events: Object.assign({}, FieldHtml.prototype.events, {
        'click a[type="object"]': '_onClickObject'
    }),
    init() {
        this._super(...arguments);
        if (!device.isMobile) {
            bus.on("DOM_updated", this, () => {
                const $editable = this.$el.find('.note-editable');
                if ($editable.length) {
                    const minHeight = window.innerHeight - $editable.offset().top - 30;
                    $editable.css('min-height', minHeight + 'px');
                }
            });
        }
    },
    /**
     * Handle the click on a link with object as type
     * @param {*} event
     */
    _onClickObject: async function (event) {
        event.preventDefault();
        const action = await this._rpc({
            model: this.model,
            method: event.target.name,
            args: [this.res_id],
            context: this.record.context,
        });
        if (action) {
            this.do_action(action);
        }
    }
});

fieldRegistry.add('html_with_action', FieldHtmlWithAction);
