/** @odoo-module **/

import { registry } from "@web/core/registry";
import {
    serializeDate,
    serializeDateTime,
} from "@web/core/l10n/dates";

/**
 * Configuration depending on the granularity, using Luxon DateTime objects:
 * @param {function} startOf function to get a DateTime at the beginning of a period
 *                           from another DateTime.
 * @param {int} cycle amount of 'granularity' periods constituting a cycle. The cycle duration
 *                    is arbitrary for each granularity:
 * cycle    ---    granularity
 * ___________________________
 * 1 day           hour
 * 1 week          day
 * 1 week          week    # there is no greater time period that takes an integer amount of weeks
 * 1 year          month
 * 1 year          quarter
 * 1 year          year    # we are not using a greater time period in Odoo (yet)
 * @param {int} cyclePos function to get the position (index) in the cycle from a DateTime.
 *                       {1} is the first index. {+1} is used for properties which have an index
 *                       starting from 0, to standardize between granularities.
 */
export const GRANULARITY_TABLE = {
    hour: {
        startOf: (x) => x.startOf("hour"),
        cycle: 24,
        cyclePos: (x) => x.hour + 1,
    },
    day: {
        startOf: (x) => x.startOf("day"),
        cycle: 7,
        cyclePos: (x) => x.weekday,
    },
    week: {
        startOf: (x) => x.startOf("week"),
        cycle: 1,
        cyclePos: (x) => 1,
    },
    month: {
        startOf: (x) => x.startOf("month"),
        cycle: 12,
        cyclePos: (x) => x.month,
    },
    quarter: {
        startOf: (x) => x.startOf("quarter"),
        cycle: 4,
        cyclePos: (x) => x.quarter,
    },
    year: {
        startOf: (x) => x.startOf("year"),
        cycle: 1,
        cyclePos: (x) => 1,
    },
};

/**
 * fill_temporal period:
 *   Represents a specific date/time range for a specific model, field and granularity.
 *
 * It is used to add new domain and context constraints related to a specific date/time
 * field, in order to configure the _read_group_fill_temporal (see core models.py)
 * method. It will be used when we want to get continuous groups in chronological
 * order in a specific date/time range.
 */
export class FillTemporalPeriod {
    /**
     * This constructor is meant to be used only by the FillTemporalService (see below)
     *
     * @param {string} modelName directly taken from model.loadParams.modelName.
     *                           this is the `res_model` from the action (i.e. `crm.lead`)
     * @param {Object} field a dictionary with keys "name" and "type".
     *                        name: Name of the field on which the fill_temporal should apply
     *                              (i.e. 'date_deadline')
     *                        type: 'date' or 'datetime'
     * @param {string} granularity can either be : hour, day, week, month, quarter, year
     * @param {integer} minGroups minimum amount of groups to display, regardless of other
     *                            constraints
     */
    constructor(modelName, field, granularity, minGroups) {
        this.modelName = modelName;
        this.field = field;
        this.granularity = granularity || "month";
        this.setMinGroups(minGroups);

        this._computeStart();
        this._computeEnd();
    }
    /**
     * Compute this.start: the DateTime for the start of the period containing
     * the current time ("now").
     * i.e. 2020-10-01 13:43:17 -> the current "hour" DateTime started at:
     *      2020-10-01 13:00:00
     *
     * @private
     */
    _computeStart() {
        this.start = GRANULARITY_TABLE[this.granularity].startOf(luxon.DateTime.now());
    }
    /**
     * Compute this.end: the DateTime for the end of the fill_temporal period.
     * This bound is exclusive.
     * The fill_temporal period is the number of [granularity] from [start] to the end of the
     * [cycle] reached after adding [minGroups]
     * i.e. we are in october 2020 :
     *      [start] = 2020-10-01
     *      [granularity] = 'month',
     *      [cycle] = 12
     *      [minGroups] = 4,
     *      => fillTemporalPeriod = 15 months (until end of december 2021)
     *
     * @private
     */
    _computeEnd() {
        const cycle = GRANULARITY_TABLE[this.granularity].cycle;
        const cyclePos = GRANULARITY_TABLE[this.granularity].cyclePos(this.start);
        // fillTemporalPeriod formula explanation :
        // We want to know how many steps need to be taken from the current position until the end
        // of the cycle reached after guaranteeing minGroups positions. Let's call this cycle (C).
        //
        // (1) compute the steps needed to reach the last position of the current cycle, from the
        //     current position:
        //     {cycle - cyclePos}
        //
        // (2) ignore {minGroups - 1} steps from the position reached in (1). Now, the current
        //     position is somewhere in (C). One step from minGroups is reserved to reach the first
        //     position after (C), hence {-1}
        //
        // (3) compute the additional steps needed to reach the last position of (C), from the
        //     position reached in (2):
        //     {cycle - (minGroups - 1) % cycle}
        //
        // (4) combine (1) and (3), the sum should not be greater than a full cycle (-> truncate):
        //     {(2 * cycle - (minGroups - 1) % cycle - cyclePos) % cycle}
        //
        // (5) add minGroups!
        const fillTemporalPeriod = ((2 * cycle - ((this.minGroups - 1) % cycle) - cyclePos) % cycle) + this.minGroups;
        this.end = this.start.plus({[`${this.granularity}s`]: fillTemporalPeriod});
        this.computedEnd = true;
    }
    /**
     * The server needs a date/time in UTC, but we don't want a day shift in case
     * of dates, even if the date is not in UTC
     *
     * @param {DateTime} bound the DateTime to be formatted (this.start or this.end)
     */
    _getFormattedServerDate(bound) {
        if (this.field.type === "date") {
            return serializeDate(bound);
        } else {
            return serializeDateTime(bound);
        }
    }
    /**
     * @param {Object} configuration
     * @param {Array[]} [domain]
     * @param {boolean} [forceStartBound=true] whether this.start DateTime must be used as a domain
     *                                         constraint to limit read_group results or not
     * @param {boolean} [forceEndBound=true] whether this.end DateTime must be used as a domain
     *                                       constraint to limit read_group results or not
     * @returns {Array[]} new domain
     */
    getDomain({ domain, forceStartBound = true, forceEndBound = true }) {
        if (!forceEndBound && !forceStartBound) {
            return domain;
        }
        const originalDomain = domain.length ? ["&", ...domain] : [];
        const defaultDomain = ["|", [this.field.name, "=", false]];
        const linkDomain = forceStartBound && forceEndBound ? ["&"] : [];
        const startDomain = !forceStartBound ? [] : [[this.field.name, ">=", this._getFormattedServerDate(this.start)]];
        const endDomain = !forceEndBound ? [] : [[this.field.name, "<", this._getFormattedServerDate(this.end)]];
        return [...originalDomain, ...defaultDomain, ...linkDomain, ...startDomain, ...endDomain];
    }
    /**
     * The default value of forceFillingTo is false when this.end is the
     * computed one, and true when it is manually set. This is because the default value of
     * this.end is computed without any knowledge of the existing data, and as such, we only
     * want to get continuous groups until the last group with data (no need to force until
     * this.end). On the contrary, when we set this.end, this means that we want groups until
     * that date.
     *
     * @param {Object} configuration
     * @param {Object} [context]
     * @param {boolean} [forceFillingFrom=true] fill_temporal must apply from:
     *                                          true: this.start
     *                                          false: the first group with at least one record
     * @param {boolean} [forceFillingTo=!this.computedEnd] fill_temporal must apply until:
     *                                          true: this.end
     *                                          false: the last group with at least one record
     * @returns {Object} new context
     */
    getContext({ context, forceFillingFrom = true, forceFillingTo = !this.computedEnd }) {
        const fillTemporal = {
            min_groups: this.minGroups,
        };
        if (forceFillingFrom) {
            fillTemporal.fill_from = this._getFormattedServerDate(this.start);
        }
        if (forceFillingTo) {
            // smallest time interval used in Odoo for the current date type
            const minGranularity = this.field.type === "date" ? "days" : "seconds";
            fillTemporal.fill_to = this._getFormattedServerDate(this.end.minus({[minGranularity]: 1}));
        }
        context = { ...context, fill_temporal: fillTemporal };
        return context;
    }
    /**
     * @param {integer} minGroups minimum amount of groups to display, regardless of other
     *                            constraints
     */
    setMinGroups(minGroups) {
        this.minGroups = minGroups || 1;
    }
    /**
     * sets the end of the period to the desired DateTime. It must be greater
     * than start. Changes the default behavior of getContext forceFillingTo
     * (becomes true instead of false)
     *
     * @param {DateTime} end
     */
    setEnd(end) {
        this.end = luxon.DateTime.max(this.start, end);
        this.computedEnd = false;
    }
    /**
     * sets the start of the period to the desired DateTime. It must be smaller than end
     *
     * @param {DateTime} start
     */
    setStart(start) {
        this.start = luxon.DateTime.min(this.end, start);
    }
    /**
     * Adds one "granularity" period to [this.end], to expand the current fill_temporal period
     */
    expand() {
        this.setEnd(this.end.plus({[`${this.granularity}s`]: 1}));
    }
}

/**
 * fill_temporal Service
 *
 * This service will be used to generate or retrieve fill_temporal periods
 *
 * A specific fill_temporal period configuration will always refer to the same instance
 * unless forceRecompute is true
 */
export const fillTemporalService = {
    start() {
        const _fillTemporalPeriods = {};

        /**
         * Get a fill_temporal period according to the configuration.
         * The default initial fill_temporal period is the number of [granularity] from [start]
         * to the end of the [cycle] reached after adding [minGroups]
         * i.e. we are in october 2020 :
         *      [start] = 2020-10-01
         *      [granularity] = 'month',
         *      [cycle] = 12 (one year)
         *      [minGroups] = 4,
         *      => fillTemporalPeriod = 15 months (until the end of december 2021)
         * Once created, a fill_temporal period for a specific configuration will be stored
         * until requested again. This allows to manipulate the period and store the changes
         * to it. This also allows to keep the configuration when switching to another view
         *
         * @param {Object} configuration
         * @param {string} [modelName] directly taken from model.loadParams.modelName.
         *                             this is the `res_model` from the action (i.e. `crm.lead`)
         * @param {Object} [field] a dictionary with keys "name" and "type".
         * @param {string} [field.name] name of the field on which the fill_temporal should apply
         *                              (i.e. 'date_deadline')
         * @param {string} [field.type] date field type: 'date' or 'datetime'
         * @param {string} [granularity] can either be : hour, day, week, month, quarter, year
         * @param {integer} [minGroups=4] optional minimal amount of desired groups
         * @param {boolean} [forceRecompute=false] optional whether the fill_temporal period should be
         *                                         reinstancied
         * @returns {FillTemporalPeriod}
         */
        const getFillTemporalPeriod = ({ modelName, field, granularity, minGroups = 4, forceRecompute = false }) => {
            if (!(modelName in _fillTemporalPeriods)) {
                _fillTemporalPeriods[modelName] = {};
            }
            if (!(field.name in _fillTemporalPeriods[modelName])) {
                _fillTemporalPeriods[modelName][field.name] = {};
            }
            if (!(granularity in _fillTemporalPeriods[modelName][field.name]) || forceRecompute) {
                _fillTemporalPeriods[modelName][field.name][granularity] = new FillTemporalPeriod(
                    modelName,
                    field,
                    granularity,
                    minGroups
                );
            } else if (_fillTemporalPeriods[modelName][field.name][granularity].minGroups != minGroups) {
                _fillTemporalPeriods[modelName][field.name][granularity].setMinGroups(minGroups);
            }
            return _fillTemporalPeriods[modelName][field.name][granularity];
        };
        return { getFillTemporalPeriod };
    },
};

registry.category("services").add("fillTemporalService", fillTemporalService);
