/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { loadJS, loadCSS } from "@web/core/assets";
import { useService } from "@web/core/utils/hooks";
import { useModelWithSampleData } from "@web/model/model";
import { standardViewProps } from "@web/views/standard_view_props";
import { useSetupAction } from "@web/search/action_hook";
import { Layout } from "@web/search/layout";
import { usePager } from "@web/search/pager_hook";
import { SearchBar } from "@web/search/search_bar/search_bar";
import { useSearchBarToggler } from "@web/search/search_bar/search_bar_toggler";
import { CogMenu } from "@web/search/cog_menu/cog_menu";

import { Component, onWillUnmount, onWillStart } from "@odoo/owl";

export class MapController extends Component {
    static template = "web_map.MapView";
    static components = {
        Layout,
        SearchBar,
        CogMenu,
    };
    static props = {
        ...standardViewProps,
        Model: Function,
        modelParams: Object,
        Renderer: Function,
        buttonTemplate: String,
    };

    setup() {
        this.action = useService("action");

        /** @type {typeof MapModel} */
        const Model = this.props.Model;
        const model = useModelWithSampleData(Model, this.props.modelParams);
        this.model = model;

        onWillUnmount(() => {
            this.model.stopFetchingCoordinates();
        });

        useSetupAction({
            getLocalState: () => {
                return this.model.metaData;
            },
        });

        onWillStart(() =>
            Promise.all([
                loadJS("/web_map/static/lib/leaflet/leaflet.js"),
                loadCSS("/web_map/static/lib/leaflet/leaflet.css"),
            ])
        );

        usePager(() => {
            return {
                offset: this.model.metaData.offset,
                limit: this.model.metaData.limit,
                total: this.model.data.count,
                onUpdate: ({ offset, limit }) => this.model.load({ offset, limit }),
            };
        });
        this.searchBarToggler = useSearchBarToggler();
    }

    /**
     * @returns {any}
     */
    get rendererProps() {
        return {
            model: this.model,
            onMarkerClick: this.openRecords.bind(this),
        };
    }

    /**
     * Redirects to views when clicked on open button in marker popup.
     *
     * @param {number[]} ids
     */
    openRecords(ids) {
        if (ids.length > 1) {
            this.action.doAction({
                type: "ir.actions.act_window",
                name: this.env.config.getDisplayName() || _t("Untitled"),
                views: [
                    [false, "list"],
                    [false, "form"],
                ],
                res_model: this.props.resModel,
                domain: [["id", "in", ids]],
            });
        } else {
            this.action.switchView("form", { resId: ids[0] });
        }
    }
}
