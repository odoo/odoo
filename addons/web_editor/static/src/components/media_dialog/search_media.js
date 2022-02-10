/** @odoo-module **/

import { throttle } from '@web/core/utils/timing';

const { Component, xml } = owl;

export class SearchMedia extends Component {
    setup() {
        this.search = throttle((ev) => this.props.search(ev.target.value), 1000);
    }
}
SearchMedia.template = xml`
<div class="input-group mr-auto">
    <input type="text" class="form-control o_we_search" t-att-placeholder="props.searchPlaceholder.trim()" t-att-value="props.needle" t-on-input="search"/>
    <div class="input-group-append">
        <div class="input-group-text o_we_search_icon">
            <i class="fa fa-search" title="Search" role="img" aria-label="Search"/>
        </div>
    </div>
</div>`;
