import { useBus } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { ListRenderer } from "@web/views/list/list_renderer";

patch(ListRenderer.prototype, {
    setup() {
        super.setup();
        if (this.env.searchModel) {
            useBus(this.env.searchModel, "insert-embedded-view", (ev) => {
                Object.assign(ev.detail, {
                    orderBy: JSON.stringify(this.props.list.orderBy),
                    keyOptionalFields: this.keyOptionalFields,
                });
            });
        }
    },

    /**
     * When the user hides/shows some columns from the list view, the system will
     * add a new cache entry in the local storage of the user and will list all
     * visible columns for the current view. To make the configuration specific to
     * a view, the system generates a unique key for the cache entry by using all
     * available information about the view.
     *
     * When loading the view, the system regenerates a key from the current view
     * and check if there is any entry in the cache for that key. If there is a
     * match, the system will load the configuration specified in the cache entry.
     *
     * For the embedded views of Knowledge, we want the configuration of the view
     * to be unique for each embedded view. To achieve that, we will overwrite the
     * function generating the key for the cache entry and include the unique id
     * of the embedded view.
     *
     * @override
     * @returns {string}
     */
    createViewKey() {
        if (this.env.searchModel?.context.knowledgeEmbeddedViewId) {
            return `${super.createViewKey()},${this.env.searchModel.context.knowledgeEmbeddedViewId}`;
        }
        return super.createViewKey();
    },
});
