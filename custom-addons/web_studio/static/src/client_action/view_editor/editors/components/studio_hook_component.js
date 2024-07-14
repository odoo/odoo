/** @odoo-module **/
import { Component, xml } from "@odoo/owl";

const formGrid = xml`
    <div class="o_web_studio_hook"
        t-attf-class="g-col-sm-{{ props.colSpan }}"
        t-att-data-xpath="props.xpath"
        t-att-data-position="props.position"
        t-att-data-type="props.type">
            <span class="o_web_studio_hook_separator" />
    </div>
`;

const kanbanRecord = xml`
    <span class="o_web_studio_hook"
        t-att-data-xpath="props.xpath"
        t-att-data-position="props.position"
        t-att-data-type="props.type" />
`;

const defaultTemplate = xml`
<div class="o_web_studio_hook" t-att-data-xpath="props.xpath" t-att-data-position="props.position" t-att-data-type="props.type" t-att-data-infos="props.infos">
    <span class="o_web_studio_hook_separator" />
</div>
`;

export class StudioHook extends Component {
    getTemplate(templateName) {
        return this.constructor.subTemplates[templateName || "defaultTemplate"];
    }
}
StudioHook.template = xml`<t t-call="{{ getTemplate(props.subTemplate) }}" />`;
StudioHook.props = ["xpath?", "position?", "type?", "colSpan?", "subTemplate?", "width?", "infos?"];
StudioHook.subTemplates = {
    formGrid,
    defaultTemplate,
    kanbanRecord,
};
