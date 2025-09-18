// @ts-check

/** @module @web/components/record_selectors/base_record_selector - Base class for record selector components with display name loading infrastructure */

import { Component, onWillStart, onWillUpdateProps } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
/**
 * Base class for single-record and multi-record selector components.
 *
 * Provides shared infrastructure: nameService setup, lifecycle hooks that
 * trigger display-name loading, and the isAvatarModel heuristic.
 *
 * Subclasses must implement:
 *   - getIds(props)               — IDs to pass to nameService.loadDisplayNames
 *   - applyDisplayNames(props, displayNames) — write loaded names to component state
 */
export class BaseRecordSelector extends Component {
    setup() {
        /** @type {import("@web/core").NameService} */
        this.nameService = useService("name");
        onWillStart(() => this.computeDerivedParams());
        onWillUpdateProps((nextProps) => this.computeDerivedParams(nextProps));
    }

    /** @returns {boolean} whether the target model supports avatar images */
    get isAvatarModel() {
        // bof
        return [
            "res.partner",
            "res.users",
            "hr.employee",
            "hr.employee.public",
        ].includes(this.props.resModel);
    }

    /**
     * Load display names and apply them to component state.
     * @param {Object} [props] - component props to use (defaults to this.props)
     */
    async computeDerivedParams(props = this.props) {
        const displayNames = await this.getDisplayNames(props);
        this.applyDisplayNames(props, displayNames);
    }

    /**
     * Fetch display names from the name service.
     * @param {Object} props - component props containing resModel
     * @returns {Promise<Record<number, string>>} map of record ID to display name
     */
    async getDisplayNames(props) {
        const ids = this.getIds(props);
        return this.nameService.loadDisplayNames(props.resModel, ids);
    }

    /**
     * Override to return the IDs that should be looked up.
     * @param {Object} [props] - component props (defaults to this.props)
     * @returns {number[]} record IDs to resolve
     */
    getIds(props = this.props) {
        return [];
    }

    /**
     * Override to write loaded display names into component state.
     * @param {Object} props - component props
     * @param {Record<number, string>} displayNames - map of ID to display name
     */
    applyDisplayNames(props, displayNames) {}
}
