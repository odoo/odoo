/** @odoo-module **/

import { SearchBar } from "@web/search/search_bar/search_bar";
import { ForecastSearchBarMenu } from "./forecast_search_bar_menu";

/**
 * This is the conversion of ForecastModelExtension. See there for more
 * explanations of what is done here.
 */

export class ForecastSearchBar extends SearchBar {}

ForecastSearchBar.components.SearchBarMenu = ForecastSearchBarMenu;
