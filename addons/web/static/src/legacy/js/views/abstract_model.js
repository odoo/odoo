/** @odoo-module alias=web.AbstractModel **/

/**
 * An AbstractModel is the M in MVC.  We tend to think of MVC more on the server
 * side, but we are talking here on the web client side.
 *
 * The duties of the Model are to fetch all relevant data, and to make them
 * available for the rest of the view.  Also, every modification to that data
 * should pass through the model.
 *
 * Note that the model is not a widget, it does not need to be rendered or
 * appended to the dom.  However, it inherits from the EventDispatcherMixin,
 * in order to be able to notify its parent by bubbling events up.
 *
 * The model is able to generate sample (fake) data when there is no actual data
 * in database.  This feature can be activated by instantiating the model with
 * param "useSampleModel" set to true.  In this case, the model instantiates a
 * duplicated version of itself, parametrized to call a SampleServer (JS)
 * instead of doing RPCs.  Here is how it works: the main model first load the
 * data normally (from database), and then checks whether the result is empty or
 * not.  If it is, it asks the sample model to load with the exact same params,
 * and it thus enters in "sample" mode.  The model keeps doing this at reload,
 * but only if the (re)load params haven't changed: as soon as a param changes,
 * the "sample" mode is left, and it never enters it again in the future (in the
 * lifetime of the model instance).  To access those sample data from the outside,
 * 'get' must be called with the the option "withSampleData" set to true.  In
 * this case, if the main model is in "sample" mode, it redirects the call to the
 * sample model.
 */

import fieldUtils from 'web.field_utils';
import mvc from 'web.mvc';
import SampleServer from 'web.SampleServer';


var AbstractModel = mvc.Model.extend({
    /**
     * @param {Widget} parent
     * @param {Object} [params={}]
     * @param {Object} [params.fields]
     * @param {string} [params.modelName]
     * @param {boolean} [params.isSampleModel=false] if true, will fetch data
     *   from a SampleServer instead of doing RPCs
     * @param {boolean} [params.useSampleModel=false] if true, will use a sample
     *   model to generate sample data when there is no "real" data in database
     * @param {AbstractModel} [params.SampleModel] the AbstractModel class
     *   to instantiate as sample model. This model won't do any rpc, but will
     *   rather call a SampleServer that will generate sample data. This param
     *   must be set when params.useSampleModel is true.
     */
    init(parent, params = {}) {
        this._super(...arguments);
        this.useSampleModel = params.useSampleModel || false;
        if (params.isSampleModel) {
            this.isSampleModel = true;
            this.sampleServer = new SampleServer(params.modelName, params.fields);
        } else if (this.useSampleModel) {
            const sampleModelParams = Object.assign({}, params, {
                isSampleModel: true,
                SampleModel: null,
                useSampleModel: false,
            });
            this.sampleModel = new params.SampleModel(this, sampleModelParams);
            this._isInSampleMode = false;
        }
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Override to call get on the sampleModel when we are in sample mode, and
     * option 'withSampleData' is set to true.
     *
     * @override
     * @param {any} _
     * @param {Object} [options]
     * @param {boolean} [options.withSampleData=false]
     */
    get(_, options) {
        let state;
        if (options && options.withSampleData && this._isInSampleMode) {
            state = this.sampleModel.__get(...arguments);
        } else {
            state = this.__get(...arguments);
        }
        return state;
    },
    /**
     * Under some conditions, the model is designed to generate sample data if
     * there is no real data in database. This function returns a boolean which
     * indicates the mode of the model: if true, we are in "sample" mode.
     *
     * @returns {boolean}
     */
    isInSampleMode() {
        return !!this._isInSampleMode;
    },
    /**
     * Disables the sample data (forever) on this model instance.
     */
    leaveSampleMode() {
        if (this.useSampleModel) {
            this.useSampleModel = false;
            this._isInSampleMode = false;
            this.sampleModel.destroy();
        }
    },
    /**
     * Override to check if we need to call the sample model (and if so, to do
     * it) after loading the data, in the case where there is no real data to
     * display.
     *
     * @override
     */
    async load(params) {
        this.loadParams = params;
        const handle = await this.__load(...arguments);
        await this._callSampleModel('__load', handle, ...arguments);
        return handle;
    },
    /**
     * When something changes, the data may need to be refetched.  This is the
     * job for this method: reloading (only if necessary) all the data and
     * making sure that they are ready to be redisplayed.
     * Sometimes, we reload the data with the "same" params as the initial load
     * params (see '_haveParamsChanged'). When we do, if we were in "sample" mode,
     * we call again the sample server after the reload if there is still no data
     * to display. When the parameters change, we automatically leave "sample"
     * mode.
     *
     * @param {any} _
     * @param {Object} [params]
     * @returns {Promise}
     */
    async reload(_, params) {
        const handle = await this.__reload(...arguments);
        if (this._isInSampleMode) {
            if (!this._haveParamsChanged(params)) {
                await this._callSampleModel('__reload', handle, ...arguments);
            } else {
                this.leaveSampleMode();
            }
        }
        return handle;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {string} method
     * @param {any} handle
     * @param  {...any} args
     * @returns {Promise}
     */
    async _callSampleModel(method, handle, ...args) {
        if (this.useSampleModel && this._isEmpty(handle)) {
            try {
                if (method === '__load') {
                    await this.sampleModel.__load(...args);
                } else if (method === '__reload') {
                    await this.sampleModel.__reload(...args);
                }
                this._isInSampleMode = true;
            } catch (error) {
                if (error instanceof SampleServer.UnimplementedRouteError) {
                    this.leaveSampleMode();
                } else {
                    throw error;
                }
            }
        } else {
            this.leaveSampleMode();
        }
    },
    /**
     * @private
     * @returns {Object}
     */
    __get() {
        return {};
    },
    /**
     * This function can be overriden to determine if the result of a load or
     * a reload is empty. In the affirmative, we will try to generate sample
     * data to prevent from having an empty state to display.
     *
     * @private
     * @params {any} handle, the value returned by a load or a reload
     * @returns {boolean}
     */
    _isEmpty(/* handle */) {
        return false;
    },
    /**
     * To override to do the initial load of the data (this function is supposed
     * to be called only once).
     *
     * @private
     * @returns {Promise}
     */
    async __load() {
        return Promise.resolve();
    },
    /**
     * Processes date(time) and selection field values sent by the server.
     * Converts data(time) values to moment instances.
     * Converts false values of selection fields to 0 if 0 is a valid key,
     * because the server doesn't make a distinction between false and 0, and
     * always sends false when value is 0.
     *
     * @param {Object} field the field description
     * @param {*} value
     * @returns {*} the processed value
     */
    _parseServerValue: function (field, value) {
        if (field.type === 'date' || field.type === 'datetime') {
            // process date(time): convert into a moment instance
            value = fieldUtils.parse[field.type](value, field, {isUTC: true});
        } else if (field.type === 'selection' && value === false) {
            // process selection: convert false to 0, if 0 is a valid key
            var hasKey0 = _.find(field.selection, function (option) {
                return option[0] === 0;
            });
            value = hasKey0 ? 0 : value;
        }
        return value;
    },
    /**
     * To override to reload data (this function may be called several times,
     * after the initial load has been done).
     *
     * @private
     * @returns {Promise}
     */
    async __reload() {
        return Promise.resolve();
    },
    /**
     * Determines whether or not the given params (reload params) differ from
     * the initial ones (this.loadParams). This is used to leave "sample" mode
     * as soon as a parameter (e.g. domain) changes.
     *
     * @private
     * @param {Object} [params={}]
     * @param {Object} [params.context]
     * @param {Array[]} [params.domain]
     * @param {Object} [params.timeRanges]
     * @param {string[]} [params.groupBy]
     * @returns {boolean}
     */
    _haveParamsChanged(params = {}) {
        for (const key of ['context', 'domain', 'timeRanges']) {
            if (key in params) {
                const diff = JSON.stringify(params[key]) !== JSON.stringify(this.loadParams[key]);
                if (diff) {
                    return true;
                }
            }
        }
        if (this.useSampleModel && 'groupBy' in params) {
            return JSON.stringify(params.groupBy) !== JSON.stringify(this.loadParams.groupedBy);
        }
    },
    /**
     * Override to redirect all rpcs to the SampleServer if this.isSampleModel
     * is true.
     *
     * @override
     */
    async _rpc() {
        if (this.isSampleModel) {
            return this.sampleServer.mockRpc(...arguments);
        }
        return this._super(...arguments);
    },
});

export default AbstractModel;
