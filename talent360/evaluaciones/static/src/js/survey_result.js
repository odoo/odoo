/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { loadBundle } from "@web/core/assets";
import publicWidget from "@web/legacy/js/public/public_widget";

// The given colors are the same as those used by D3
var D3_COLORS = ["#1f77b4","#ff7f0e","#aec7e8","#ffbb78","#2ca02c","#98df8a","#d62728",
                    "#ff9896","#9467bd","#c5b0d5","#8c564b","#c49c94","#e377c2","#f7b6d2",
                    "#7f7f7f","#c7c7c7","#bcbd22","#dbdb8d","#17becf","#9edae5"];

// TODO awa: this widget loads all records and only hides some based on page
// -> this is ugly / not efficient, needs to be refactored
publicWidget.registry.SurveyResultPagination = publicWidget.Widget.extend({
    events: {
        'click li.o_survey_js_results_pagination a': '_onPageClick',
        "click .o_survey_question_answers_show_btn": "_onShowAllAnswers",
    },

    //--------------------------------------------------------------------------
    // Widget
    //--------------------------------------------------------------------------

    /**
     * @override
     * @param {$.Element} params.questionsEl The element containing the actual questions
     *   to be able to hide / show them based on the page number
     */
    init: function (parent, params) {
        this._super.apply(this, arguments);
        this.$questionsEl = params.questionsEl;
    },

    /**
     * @override
     */
    start: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            self.limit = self.$el.data("record_limit");
        });
    },

    // -------------------------------------------------------------------------
    // Handlers
    // -------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onPageClick: function (ev) {
        ev.preventDefault();
        this.$('li.o_survey_js_results_pagination').removeClass('active');

        var $target = $(ev.currentTarget);
        $target.closest('li').addClass('active');
        this.$questionsEl.find("tbody tr").addClass("d-none");

        var num = $target.text();
        var min = this.limit * (num - 1) - 1;
        if (min === -1) {
            this.$questionsEl
                .find("tbody tr:lt(" + this.limit * num + ")")
                .removeClass("d-none");
        } else {
            this.$questionsEl
                .find("tbody tr:lt(" + this.limit * num + "):gt(" + min + ")")
                .removeClass("d-none");
        }
    },

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onShowAllAnswers: function (ev) {
        const btnEl = ev.currentTarget;
        const pager = btnEl.previousElementSibling;
        btnEl.classList.add("d-none");
        this.$questionsEl.find("tbody tr").removeClass("d-none");
        pager.classList.add("d-none");
        this.$questionsEl.parent().addClass("h-auto");
    },
});

/**
 * Widget responsible for the initialization and the drawing of the various charts.
 *
 */
publicWidget.registry.SurveyResultChart = publicWidget.Widget.extend({

    //--------------------------------------------------------------------------
    // Widget
    //--------------------------------------------------------------------------

    /**
     * Initializes the widget based on its defined graph_type and loads the chart.
     *
     * @override
     */
    start: function () {
        var self = this;

        return this._super.apply(this, arguments).then(function () {
            self.graphData = self.$el.data("graphData");

            self.labels = self.graphData.map(function (respuesta) {
                return respuesta.texto;
            });
    
            self.counts = self.graphData.map(function (respuesta) {
                return respuesta.conteo;
            });
    

            if (self.graphData && self.graphData.length !== 0) {
                switch (self.$el.data("graphType")) {
                    case 'bar':
                        self.chartConfig = self._getBarChartConfig();
                        break;
                    case 'pie':
                        self.chartConfig = self._getPieChartConfig();
                        break;
                }
                window.addEventListener("afterprint", self._onAfterPrint.bind(self));
                window.addEventListener("beforeprint", self._onBeforePrint.bind(self));
                self.chart = self._loadChart();
            }
        });
    },

    willStart: async function () {
        await loadBundle("web.chartjs_lib");
    },

    // -------------------------------------------------------------------------
    // Handlers
    // -------------------------------------------------------------------------

    /**
     * Prepare chart for media print
     * @private
     */
    _onBeforePrint: function () {
        const printWidth = 630; // Value to fit any graphic into the width of an A4 portrait page
        this.chart.resize(printWidth, Math.floor(printWidth / this.chart.aspectRatio));
    },

    /**
     * Turn back chart to original size, for media screen
     * @private
     */
    _onAfterPrint: function () {
        this.chart.resize();
    },

    // -------------------------------------------------------------------------
    // Private
    // -------------------------------------------------------------------------

    /**
     * Returns a standard bar chart configuration.
     *
     * @private
     */
    _getBarChartConfig: function () {
        return {
            type: 'bar',
            data: {
                labels: this.labels,
                datasets:[{
                    label: "Conteo",
                    data: this.counts,
                    backgroundColor: this.counts.map(function (val, index) {
                        return D3_COLORS[index % 20];
                    }),
                }]
            },
            options: {
                plugins: {
                    legend: {
                        display: false,
                    },
                    tooltip: {
                        enabled: false,
                    },
                },
                scales: {
                    x: {
                        ticks: {
                            callback: function (val, index) {
                                // For a category axis, the val is the index so the lookup via getLabelForValue is needed
                                const value = this.getLabelForValue(val);
                                const tickLimit = 35;
                                return value?.length > tickLimit
                                    ? `${value.slice(0, tickLimit)}...`
                                    : value;
                            },
                        },
                    },
                    y: {
                        ticks: {
                            precision: 0,
                        },
                        beginAtZero: true,
                    },
                },
            },
        };
    },

    /**
     * Returns a standard pie chart configuration.
     *
     * @private
     */
    _getPieChartConfig: function () {
        var ans = {
            type: 'pie',
            data: {
                labels: this.labels,
                datasets: [{
                    label: '',
                    data: this.counts,
                    backgroundColor: this.counts.map(function (val, index) {
                        return D3_COLORS[index % 20];
                    }),
                }]
            },
            options: {
                aspectRatio: 2,
            },
        };
        console.log(ans);
        return ans;
    },

    /**
     * Loads the chart using the provided Chart library.
     *
     * @private
     */
    _loadChart: function () {
        this.$el.css({position: 'relative'});
        var $canvas = this.$('canvas');
        var ctx = $canvas.get(0).getContext('2d');
        return new Chart(ctx, this.chartConfig);
    },

});

publicWidget.registry.SurveyResultWidget = publicWidget.Widget.extend({
    selector: '.o_survey_result',
    events: {
        "click .o_survey_results_print": "_onPrintResultsClick",
    },

    //--------------------------------------------------------------------------
    // Widget
    //--------------------------------------------------------------------------

    /**
    * @override
    */
    start: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            var allPromises = [];
            self.$('.pagination_wrapper').each(function (){
                var questionId = $(this).data("question_id");
                allPromises.push(new publicWidget.registry.SurveyResultPagination(self, {
                    'questionsEl': self.$('#survey_table_question_'+ questionId)
                }).attachTo($(this)));
            });

            self.$('.survey_graph').each(function () {
                var chartWidget = new publicWidget.registry.SurveyResultChart(self);
                allPromises.push(chartWidget.attachTo($(this)));
            }); 

            if (allPromises.length !== 0) {
                return Promise.all(allPromises).finally(seleccionarTab);
            } else {
                return Promise.resolve();
            }
        });
    },

    /**
     * Call print dialog
     * @private
     */
    _onPrintResultsClick: function () {
        window.print();
    },
});


function seleccionarTab(){
    var tabs = $('.nav-tabs');
    
    tabs.each(function() {
        var children = $(this).find('a');
        var default_tab = undefined;

        children.each(function() {
            var child = $(this);
            var done = false;

            if (done) {
                return;
            }

            if (default_tab) {
                child.tab('show');
                done = true
            }

            if (child.hasClass('default')) {
                default_tab = child;
            }
        });

        if (default_tab === undefined) {
            default_tab = $(children[0]);
        }

        
        default_tab.tab('show');


    });
}

export default {
    resultWidget: publicWidget.registry.SurveyResultWidget,
    chartWidget: publicWidget.registry.SurveyResultChart,
    paginationWidget: publicWidget.registry.SurveyResultPagination
};
