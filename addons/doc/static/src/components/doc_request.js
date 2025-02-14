import { Component, useState, markup } from "@odoo/owl";
import { LANGUAGES, createRequestCode } from "@doc/utils/doc_code_gen";
import { CodeViewer } from "@doc/components/doc_code_viewer";

export class DocRequest extends Component {
    static template = "web.DocRequest";

    static components = {
        CodeViewer,
    };
    static props = {
        url: String,
        request: { optional: true },
        method: { type: String, optional: true },
    };
    static defaultProps = {
        httpMethod: "POST",
    };

    setup() {
        this.LANGUAGES = LANGUAGES;
        this.state = useState({
            exampleLanguage: LANGUAGES.json,
            exampleCode: "",
            requestCode: this.createRequestCode(LANGUAGES.json),
            response: {},
            requestTab: 0,
        });
        this.selectLanguage(localStorage.getItem("doc/code-lang") || LANGUAGES.json);
    }

    selectLanguage(language) {
        localStorage.setItem("doc/code-lang", language);
        this.state.exampleLanguage = language;
        this.state.exampleCode = this.createRequestCode(language);
    }

    createRequestCode(language) {
        return createRequestCode({
            language,
            url: window.location.origin + this.props.url,
            apiKey: this.env.modelStore.apiKey,
            requestObj: this.props.request,
        });
    }

    get htmlResponse() {
        const response = this.state.response;
        return markup(response.error || response.body);
    }

    get hasResponse() {
        return this.state.response.error || this.state.response.body;
    }

    async execute() {
        this.state.response = {};
        const result = await this.env.modelStore.executeRequest(
            this.props.url,
            this.state.requestCode
        );
        if (result) {
            this.state.response = result;
        }
    }
}
