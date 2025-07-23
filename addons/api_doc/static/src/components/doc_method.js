import { Component, useState, markup } from "@odoo/owl";
import { DocRequest } from "@api_doc/components/doc_request";
import { DocTable, TABLE_TYPES } from "@api_doc/components/doc_table";
import { getParameterDefaultValue } from "@api_doc/utils/doc_model_utils";
import { useDocUI } from "@api_doc/utils/doc_ui_store";

export class DocMethod extends Component {
    static template = "web.DocMethod";
    static components = {
        DocRequest,
        DocTable,
    };
    static props = {
        method: Object,
        class: String,
    };

    setup() {
        this.ui = useDocUI();
        this.state = useState({ open: true });
        this.parametersData = {
            headers: ["Name", "Type", "Default Value", "Description"],
            items: Object.entries(this.method.parameters).map(([name, options]) => [
                { type: TABLE_TYPES.Code, value: name },
                {
                    type: TABLE_TYPES.Code,
                    value: "annotation" in options ? options.annotation : "-",
                },
                { type: TABLE_TYPES.Code, value: this.getDefaultValue(options) },
                { type: TABLE_TYPES.Tooltip, value: markup(options.doc) || "" },
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
        return this.method.doc;
    }

    get isVertical() {
        return this.ui.size < 1400;
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
            context: {},
        };

        if (this.method.api) {
            delete request.ids;
        }

        for (const paramName in this.method.parameters) {
            const param = this.method.parameters[paramName];
            request[paramName] = getParameterDefaultValue(paramName, param);
        }

        return request;
    }
}
