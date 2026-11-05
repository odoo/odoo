import { Component, xml } from "@odoo/owl";
import { ComponentRenderer } from "./component_renderer";
import { useStories } from "../stories";

export class Canvas extends Component {
    static components = { ComponentRenderer };
    static template = xml`
        <div class="o_canvas_page d-flex flex-column">
            <div class="o_canvas_sheet h-100 overflow-auto">
                <ComponentRenderer/>
            </div>
        </div>
    `;

    setup() {
        this.stories = useStories();
    }
}
