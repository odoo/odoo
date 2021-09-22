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
                    const resizerHeight = this.$el.find('.o_wysiwyg_resizer').outerHeight();
                    const newHeight = window.innerHeight - $editable.offset().top - resizerHeight - 1;
                    $editable.outerHeight(newHeight);
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
