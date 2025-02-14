import { Component, useRef, onMounted, useExternalListener, useState } from "@odoo/owl";
import { useDebounced } from "@web/core/utils/timing";
import { search } from "@api_doc/utils/doc_model_search";

export class SearchModal extends Component {
    static template = "web.DocSearchModal";

    static components = {};
    static props = {
        close: { type: Function },
    };

    setup() {
        this.seachRef = useRef("seachRef");
        this.modalRef = useRef("modalRef");
        this.scrollRef = useRef("scrollRef");

        this.results = [];
        this.itemHeight = 45;
        this.itemMargin = 10;

        this.state = useState({
            resultCount: 0,
            results: [],
            activeFilters: {
                models: true,
                methods: true,
                fields: true,
            },
        });

        this.search = useDebounced((query) => {
            this.results = search(this.env.modelStore.models, query, this.state.activeFilters);
            this.state.resultCount = this.results.length;
            this.scrollRef.el.scrollTop = 0;
            this.onScroll(this.scrollRef.el);
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
    }

    onInput(event) {
        if (event.target.value.trim()) {
            this.search(event.target.value.trim());
        }
    }

    onSelect(result) {
        this.env.modelStore.setActiveModel(result);
        this.props.close();
    }

    onFilterClick(filter) {
        this.state.activeFilters[filter] = !this.state.activeFilters[filter];
        this.search(this.seachRef.el.value.trim());
    }

    onScroll(container) {
        const rowHeight = this.itemHeight + this.itemMargin;
        const nodePadding = 10;

        let startIndex = Math.floor(container.scrollTop / rowHeight) - nodePadding;
        startIndex = Math.max(0, startIndex);

        const viewportHeight = container.getBoundingClientRect().height;
        let visibleCount = Math.ceil(viewportHeight / rowHeight) + 2 * nodePadding;
        visibleCount = Math.min(this.results.length - startIndex, visibleCount);

        this.state.scrollHeight = this.results.length * rowHeight;
        this.state.scrollOffsetY = startIndex * rowHeight;
        this.state.results = this.results.slice(startIndex, startIndex + visibleCount);
    }
}
