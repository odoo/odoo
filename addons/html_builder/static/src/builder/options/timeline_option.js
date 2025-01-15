import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";

class TimelineOptionPlugin extends Plugin {
    static id = "TimelineOption";
    resources = {
        builder_options: [
            withSequence(5, {
                template: "html_builder.TimelineOption",
                selector: ".s_timeline",
            }),
        ],
        dropzone_selector: {
            selector: ".s_timeline_row",
            dropNear: ".s_timeline_row",
        },
    };
}

// TODO add in overlayButton
/* <xpath expr="." position="inside">
    <div data-selector=".s_timeline_row" data-drop-near=".s_timeline_row"/>
    <div data-js="Timeline" data-selector=".s_timeline_card">
        <we-button data-timeline-card="" data-no-preview="true" class="o_we_overlay_opt"><i class="fa fa-fw fa-angle-left"/><i class="fa fa-fw fa-angle-right"/></we-button>
    </div>
</xpath>
<xpath expr="//div[@data-js='SnippetMove'][contains(@data-selector,'section')]" position="attributes">
    <attribute name="data-selector" add=".s_timeline_row" separator=","/>
</xpath> */

registry.category("website-plugins").add(TimelineOptionPlugin.id, TimelineOptionPlugin);
