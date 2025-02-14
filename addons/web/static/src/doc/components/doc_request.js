import { Component, useState, xml, markup } from "@odoo/owl";
import { LANGUAGES, createRequestCode } from "@web/doc/utils/doc_code_gen";
import { CodeViewer } from "@web/doc/components/doc_code_viewer";
import { useModelStore } from "@web/doc/utils/doc_model_store";

function tryParseJSON(jsonString) {
    try {
        const json = JSON.parse(jsonString);
        return json && typeof json === "object" ? json : null;
    } catch {
        return null;
    }
}

function getFullLengthUrl(url) {
    return window.location.origin + url;
}

export class DocRequest extends Component {
    static template = xml`
        <div class="o_doc_request ps-2 h-100 border-start">
            <div class="flex justify-content-between align-items-center mb-1">
                <h3>Request</h3>
                <div class="flex">
                    <select class="me-1" t-on-change="event => this.selectLanguage(event.target.value)">
                        <option
                            t-foreach="LANGUAGES"
                            t-as="lang"
                            t-key="lang"
                            t-att-selected="state.exampleLanguage === lang"
                            t-att-value="lang"
                            t-out="lang"
                        />
                    </select>
                    <button
                        class="btn primary flex align-items-center"
                        t-on-click="execute"
                        t-att-disabled="state.exampleLanguage !== 'json'"
                    >
                        <span>Run</span>
                        <i class="fa fa-play ms-1" aria-hidden="true"></i>
                    </button>
                </div>
            </div>

            <CodeViewer
                t-if="state.exampleLanguage !== 'json'"
                language="LANGUAGES[state.exampleLanguage]"
                value="state.exampleCode"
            />
            <CodeViewer
                t-else=""
                language="'json'"
                value="state.requestCode"
                editable="true"
                onChange="value => this.state.requestCode = value"
            />

            <div class="mt-2 flex align-items-center mb-1">
                <h3>Response</h3>
                <span t-if="hasResponse and !state.response.error" class="badge success ms-1">Success</span>
                <span t-if="hasResponse and state.response.error" class="badge error ms-1">Failed</span>
            </div>

            <t t-if="hasResponse">
                <CodeViewer t-if="!state.response.error" value="state.response.body"/>
                <div t-else="" class="alert error mt-1flex flex-column">
                    <h5 class="mb-2 flex align-items-center">
                        <i class="pe-1 fa fa-exclamation-triangle" aria-hidden="true"></i>
                        <span>Error <t t-out="state.response.status"/> while executing request</span>
                    </h5>
                    <div>
                        <div t-out="htmlResponse"></div>
                    </div>
                </div>
            </t>
            <p t-else="" class="text-muted">Run to get a response</p>
        </div>
    `;

    static components = {
        CodeViewer,
    };
    static props = {
        url: String,
        request: { optional: true },
        httpMethod: { type: String, optional: true },
        method: { type: String, optional: true },
    };
    static defaultProps = {
        httpMethod: "POST",
    };

    setup() {
        this.LANGUAGES = LANGUAGES;
        this.store = useModelStore();
        this.state = useState({
            exampleLanguage: "",
            exampleCode: "",
            requestCode: this.getDefaultRequestCode(),
            response: {},
            requestTab: 0,
        });

        const lang = sessionStorage.getItem("code-lang") || LANGUAGES.json;
        this.selectLanguage(lang);
    }

    selectLanguage(language) {
        sessionStorage.setItem("code-lang", language);

        this.state.exampleLanguage = language;
        this.state.exampleCode = createRequestCode({
            language,
            url: getFullLengthUrl(this.props.url),
            apiKey: this.store.apiKey,
            requestObj: this.props.request,
        });
    }

    getDefaultRequestCode() {
        return createRequestCode({
            language: "json",
            url: getFullLengthUrl(this.props.url),
            apiKey: this.store.apiKey,
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
        if (!this.store.apiKey) {
            this.store.showApiKeyModal = true;
            return;
        }

        this.state.response.body = null;
        this.state.response.error = null;
        this.state.response.status = null;

        try {
            const apiKey = this.store.apiKey;
            const request = {
                method: this.props.httpMethod,
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${apiKey}`,
                },
            };

            if (request.method === "POST") {
                request.body = this.state.requestCode;
            }

            const response = await fetch(this.props.url, request);
            console.info("Request response", response);
            this.state.response.status = response.status;

            const body = await response.text();
            console.info("Request body\n", body);
            this.state.response[response.ok ? "body" : "error"] = body;

            const json = tryParseJSON(body);
            if (json) {
                if (response.ok) {
                    this.state.response.body = JSON.stringify(json, null, 2);
                } else {
                    const error = json;
                    console.error("Error while executing request", json);
                    this.state.response.body = null;
                    this.state.response.error = [
                        `<h3 class="mb-1">${error.message}</h3>`,
                        `<pre class="p-2">${error.debug}</pre>`,
                    ].join("\n");
                }
            }
        } catch (error) {
            this.state.response.error = error;
        }
    }
}
