
import DynamicSnippetOptions from '@website/snippets/s_dynamic_snippet/options';
import { patch } from '@web/core/utils/patch';


patch(DynamicSnippetOptions.prototype, {
    /**
     * Adds tooltips to the we-buttons according the the provided data.
     *
     * @override
     * @param {HTMLElement} selectUserValueWidgetElement the we-buttons container
     * @param {Object} data the filters data
     * @private
     */
    async _renderSelectUserValueWidgetButtons(selectUserValueWidgetElement, data) {
        await super._renderSelectUserValueWidgetButtons(selectUserValueWidgetElement, data);
        for (let id in data) {
            if (data[id].help) {
                selectUserValueWidgetElement
                    .querySelector(`[data-select-data-attribute="${id}"]`)
                    .setAttribute('title', data[id].help);
            }
        }
    },
});
