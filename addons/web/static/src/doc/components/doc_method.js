import { Component, useState, xml, markup } from "@odoo/owl";
import { DocRequest } from "@web/doc/components/doc_request";
import { DocTable } from "@web/doc/components/doc_table";

export class DocMethod extends Component {
    static template = xml`
        <article class="o-doc-method mb-2" t-att-id="this.method.name">
            <div
                class="o-doc-method-header position-sticky flex w-100 align-items-center justify-content-between cursor-pointer rounded bg-1"
                t-on-click="() => this.state.open = !this.state.open"
                t-att-class="{ ['border-bottom']: this.state.open, o_collapsed: !this.state.open }"
                role="button"
            >
                <div class="icon-btn" role="button" t-att-class="{ o_collapsed: !this.state.open }">
                    <i class="fa fa-angle-right" aria-hidden="true"></i>
                </div>
                <h4 class="flex-grow ms-1" t-out="this.method.name"></h4>
                <div class="ms-1 text-muted" t-out="this.method.module"></div>
            </div>

            <div t-if="state.open" class="o-doc-method-content p-3 bg-1">
                <div class="w-100 flex">
                    <div class="w-50 me-2">
                        <h4>Route</h4>
                        <pre t-out="this.method.url"/>

                        <t t-if="method.doc">
                            <h4 class="mt-2">Description</h4>
                            <p class="doc_method_description mb-2" t-out="doc"></p>
                        </t>

                        <t t-if="method.signature">
                            <h4 class="mt-2">Signature</h4>
                            <pre t-out="method.signature"/>
                        </t>

                        <h4 class="mt-2">Parameters</h4>
                        <DocTable
                            t-if="parametersData.items.length > 0"
                            data="parametersData"
                        />
                        <div class="text-muted" t-else="">There's no parameters for this method</div>
                    </div>
                    <div class="w-50">
                        <DocRequest
                            url="method.url"
                            request="request"
                        />
                    </div>
                </div>
            </div>
        </article>
    `;
    static components = {
        DocRequest,
        DocTable,
    };
    static props = {
        method: Object,
    };

    setup() {
        this.state = useState({ open: true });
        this.parametersData = {
            headers: ["Name", "Type", "Default Value", "Description"],
            items: Object.entries(this.method.parameters).map(([name, options]) => [
                { type: "code-like", value: name },
                { type: "code-like", value: "annotation" in options ? options.annotation : "-" },
                { type: "code-like", value: this.getDefaultValue(options) },
                { type: "tooltip", value: options.doc || "" },
            ]),
        };
    }

    get method() {
        return this.props.method;
    }

    get parameters() {
        return this.method.parameters.filter((a) => a !== "self");
    }

    get doc() {
        return markup(this.method.doc);
    }

    getDefaultValue(param) {
        if ("default" in param) {
            return typeof param.default === "string" ? `"${param.default}"` : param.default;
        } else {
            return "-";
        }
    }

    get request() {
        if (this.method.request) {
            return this.method.request;
        }

        const request = {
            ids: [],
            kwargs: {},
            context: {},
        };

        if (this.method.api) {
            delete request.ids;
        }

        for (const paramName in this.method.parameters) {
            const param = this.method.parameters[paramName];
            request.kwargs[paramName] = "default" in param ? param.default : "";
        }

        return request;
    }
}
