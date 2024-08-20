/** @odoo-module **/

import { DynamicSnippetOptions } from "@website/snippets/s_dynamic_snippet/options";
import {
    registerWebsiteOption,
} from "@website/js/editor/snippets.registry";

export class DynamicSnippetEventOptions extends DynamicSnippetOptions {
    /**
     * @override
     */
    constructor() {
        super(...arguments);
        this.modelNameFilter = 'event.event';
    }

    _setOptionsDefaultValues() {
        this._setOptionValue('numberOfRecords', 4);
        super._setOptionsDefaultValues(...arguments);
    }

}

registerWebsiteOption("DynamicSnippetEventOptions", {
    Class: DynamicSnippetEventOptions,
    template: "website_event.s_dynamic_snippet_option",
    selector: "[data-snippet='s_events']",
});
