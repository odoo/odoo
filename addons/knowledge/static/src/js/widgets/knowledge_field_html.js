/** @odoo-module **/

import fieldRegistry from 'web.field_registry';
import FieldHtml from 'web_editor.field.html';

const KnowledgeFieldHtml = FieldHtml.extend({
    DEBOUNCE: 1500, // 1500ms,
    _createWysiwygInstance: async function () {
        await this._super(...arguments);
        const editor = this.wysiwyg.odooEditor;
        editor.addEventListener('historyStep', event => {
            /**
             * When a new history step is created, we call the `_onChange` function
             * that will call the `debounce` function. Eventually, the debounce function
             * will be executed and the a `field_changed` event will be triggered.
             */
            this._onChange();
        });
    },
    /**
     * @override
     */
    _onWysiwygBlur: function () {},
});

fieldRegistry.add('knowledge_html', KnowledgeFieldHtml);

export default KnowledgeFieldHtml;
