import {
    Component,
    xml,
    useRef,
    onMounted,
    useExternalListener,
    useState,
    onWillUnmount,
} from "@odoo/owl";
import { useModelStore } from "@web/doc/utils/doc_model_store";

function debounce(func, timeout = 300) {
    let timer;
    let canceled = false;
    const fn = (...args) => {
        if (!canceled) {
            clearTimeout(timer);
            timer = setTimeout(() => func(...args), timeout);
        }
    };

    fn.cancel = () => {
        canceled = true;
        clearTimeout(timer);
    };

    return fn;
}

export class SearchModal extends Component {
    static template = xml`
        <div class="modal-bg flex justify-content-center align-items-center">
            <div class="modal p-2 flex flex-column mb-1" style="height: 40rem; width: 40rem" t-ref="modalRef">
                <input
                    class="mb-2"
                    type="text"
                    autocorrect="off"
                    placeholder="Find anything..."
                    t-on-input="onInput"
                    t-ref="seachRef"
                />

                <div class="flex flex-column w-100" style="overflow-y: auto">
                    <button
                        t-foreach="state.results"
                        t-as="result"
                        t-key="result.label"
                        class="btn mb-1 text-start w-100 flex flex-row"
                        t-on-click="() => this.onSelect(result)"
                    >
                        <div class="h-100 flex-grow">
                            <h4 t-out="result.label" class="text-ellipsis"></h4>
                            <div class="text-muted text-ellipsis" t-out="result.path"></div>
                        </div>
                        <span class="text-muted h-100" t-out="result.type"></span>
                    </button>
                </div>
            </div>
        </div>
    `;

    static components = {};
    static props = {
        close: { type: Function },
        onSelect: { type: Function },
    };

    setup() {
        this.seachRef = useRef("seachRef");
        this.modalRef = useRef("modalRef");

        this.store = useModelStore();
        this.state = useState({
            results: [],
        });
        this.search = debounce((query) => {
            const result = this.store.search(query);
            if (result && result.length > 0) {
                this.state.results = result.slice(0, Math.min(result.length, 30));
            } else {
                this.state.results = [];
            }
        }, 300);

        useExternalListener(window, "keydown", (event) => {
            if (event.key === "Escape") {
                this.props.close();
            }
        });

        useExternalListener(window, "click", (event) => {
            if (!this.modalRef.el.contains(event.target)) {
                this.props.close();
            }
        });

        onMounted(() => {
            this.seachRef.el.focus();
        });

        onWillUnmount(() => {
            this.search.cancel();
        });
    }

    onInput(event) {
        const query = event.target.value.trim();
        this.search(query);
    }

    onSelect(result) {
        this.props.onSelect(result);
        this.props.close();
    }
}
