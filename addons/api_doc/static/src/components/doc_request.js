import { Component, useState } from "@odoo/owl";
import { LANGUAGES, createRequestCode } from "@api_doc/utils/doc_code_gen";
import { CodeEditor } from "@web/core/code_editor/code_editor";

class CopyableCodeEditor extends CodeEditor {
    static template = "web.DocRequest.CodeEditor";

    copyToClipboard() {
        navigator?.clipboard?.writeText(this.aceEditor.getValue());
        this.state.copied = true;
        setTimeout(() => {
            this.state.copied = false;
        }, 1000);
    }
}

export class DocRequest extends Component {
    static template = "web.DocRequest";

    static components = {
        CodeEditor: CopyableCodeEditor,
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
        this.maxLines = Infinity;
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

    get responseText() {
        const response = this.state.response;
        return response.error || response.body;
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
