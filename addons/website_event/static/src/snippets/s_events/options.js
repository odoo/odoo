/** @odoo-module **/

import options from '@web_editor/js/editor/snippets.options';
import dynamicSnippetOptions from '@website/snippets/s_dynamic_snippet/options';

const dynamicSnippetEventOptions = dynamicSnippetOptions.extend({
    /**
     * @override
     */
    init() {
        this._super.apply(this, arguments);
        this.modelNameFilter = 'event.event';
    },

    _setOptionsDefaultValues() {
        this._setOptionValue('numberOfRecords', 4);
        this._super.apply(this, arguments);
    },

});

options.registry.event_upcoming_snippet = dynamicSnippetEventOptions;
