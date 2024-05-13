/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { loadBundle } from "@web/core/assets";
import publicWidget from "@web/legacy/js/public/public_widget";

// The given colors are the same as those used by D3
var D3_COLORS = [
    "#1f77b4","#ff7f0e","#aec7e8","#ffbb78","#2ca02c","#98df8a","#d62728",
    "#ff9896","#9467bd","#c5b0d5","#8c564b","#c49c94","#e377c2","#f7b6d2",
    "#7f7f7f","#c7c7c7","#bcbd22","#dbdb8d","#17becf","#9edae5"
];

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
            self.label = self.$el.data("label") || 'Data';


            
            // Asegurarse de que graphData es un array de objetos
            if (typeof self.graphData === 'string') {
                self.graphData = JSON.parse(self.graphData.replace(/'/g, '"'));
            }
            
            console.log("Label", self.label)
            console.log("Graph Data", self.graphData)
            
            // Verifica que graphData es un array
            if (Array.isArray(self.graphData)) {
                self.labels = self.graphData.map(function (categoria) {
                    return categoria.nombre;
                });

                self.counts = self.graphData.map(function (categoria) {
                    return categoria.valor;
                });

                self.color = self.graphData.map(function (categoria) {
                    return categoria.color;
                });

                if (self.graphData && self.graphData.length !== 0) {
                    switch (self.$el.data("graphType")) {
                        case 'bar':
                            self.chartConfig = self._getBarChartConfig();
                            break;
                        case 'col':
                            self.chartConfig = self._getColChartConfig();
                            break;
                        case 'pie':
                            self.chartConfig = self._getPieChartConfig();
                            break;
                        case 'radar':
                            self.chartConfig = self._getRadarChartConfig();
                            break;
                        case 'doughnut': 
                            self.chartConfig = self._getDoughnutChartConfig();
                            break;
                    }
                }
            } else {
                console.error("graphData is not an array:", self.graphData);
            }
            self._loadChart();
        });
    },

    willStart: async function () {
        await loadBundle("web.chartjs_lib");
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
        self = this;
        return {
            type: 'bar',
            data: {
                labels: this.labels,
                datasets:[{
                    label: this.label,
                    data: this.counts,
                    backgroundColor: this.counts.map(function (val, index) {
                        return self.color[index] || D3_COLORS[index % 20];
                    }),
                }]
            },
            options: {
                responsive: true,
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

    _getColChartConfig: function () {
        self = this;
        return {
            type: 'bar',
            data: {
                labels: this.labels,
                datasets:[{
                    label: "Conteo",
                    data: this.counts,
                    backgroundColor: this.counts.map(function (val, index) {
                        return self.color[index] || D3_COLORS[index % 20];
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
                indexAxis: 'y',
                scales: {
                    y: {
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
                    x: {
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
        self = this;
        return {
            type: 'pie',
            data: {
                labels: this.labels,
                datasets: [{
                    label: '',
                    data: this.counts,
                    backgroundColor: this.counts.map(function (val, index) {
                        return self.color[index] || D3_COLORS[index % 20];
                    }),
                }]
            },
            options: {
                aspectRatio: 2,
            },
        };
    },

    /**
     * Returns a standard radar chart configuration.
     *
     * @private
     */
    _getRadarChartConfig: function () {
        return {
            type: 'radar',
            data: {
                labels: this.labels,
                datasets: [
                {
                    label: this.label,
                    data: this.counts,
                    backgroundColor: 'rgba(255, 99, 132, 0.2)',
                    borderColor: 'rgb(255, 99, 132)',
                    pointBackgroundColor: 'rgb(255, 99, 132)',
                    pointBorderColor: '#fff',
                    pointHoverBackgroundColor: '#fff',
                    pointHoverBorderColor: 'rgb(255, 99, 132)'
                }],
            },
            options: {
                responsive: true,
                elements: {
                    line: {
                        borderWidth: 3
                    }
                }
            },
        };
    },

    /**
     * Returns a standard doughnut chart configuration.
     *
     * @private
     */
    _getDoughnutChartConfig: function () {
        self = this;
        return {
            type: 'doughnut',
            data: {
                labels: this.labels,
                datasets: [{
                    label: '',
                    data: this.counts,
                    backgroundColor: this.counts.map(function (val, index) {
                        return self.color[index] || D3_COLORS[index % 20];
                    }),
                }]
            },
            options: {
                responsive: true,
                aspectRatio: 2,
                cutout: '70%',
                plugins: {
                    legend: {
                        display: false,
                    },
                    tooltip: {
                        enabled: false,
                    },
                    centerText: {
                        display: true,
                        text: this.counts[0].toFixed(2) + '%',
                        font: {
                            size: '20'
                        }
                    },
                }
            },
            plugins: [{
                beforeDraw: function(chart) {
                    if (chart.config.options.plugins.centerText) {
                        const width = chart.width,
                            height = chart.height,
                            ctx = chart.ctx;
                        ctx.restore();
                        const fontSize = (height / 114).toFixed(2);
                        ctx.font = fontSize + "em sans-serif";
                        ctx.textBaseline = "middle";
                        const text = chart.config.options.plugins.centerText.text,
                            textX = Math.round((width - ctx.measureText(text).width) / 2),
                            textY = height / 2;
                        ctx.fillText(text, textX, textY);
                        ctx.save();
                    }
                }
            }]
        };
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
        this.chart = new Chart(ctx, this.chartConfig);
    },

    _reloadChart: function () {
        if (this.chart !== undefined) {
            this.chart.destroy();
        }
        this._loadChart();
    }
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

            self.charts = [];
            self.other_charts = [];
            self.$('.survey_graph').each(function () {
                var chartWidget = new publicWidget.registry.SurveyResultChart(self);
                allPromises.push(chartWidget.attachTo($(this)));
                // atriibuto role is tabpane
                if ($(this).attr("role") === "tabpanel") {
                    self.charts.push(chartWidget);
                }
                else {
                    self.other_charts.push(chartWidget);
                }
            }); 

            if (allPromises.length !== 0) {
                return Promise.all(allPromises).finally(() => self._attach_listener(self));
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
    
    _attach_listener: function (self){
        console.log("attatching listeners")

        for (let chart of self.charts) {
            chart._reloadChart();
        }

        for (let chart of self.other_charts) {
            chart._reloadChart();
        }

        const tabEls = document.querySelectorAll('a[data-bs-toggle="tab"][data-chart="1"]');
        tabEls.forEach(function (tabEl) {
            tabEl.addEventListener("shown.bs.tab", function (event) {
                const index = Array.from(tabEls).indexOf(event.target);
                self.charts[index]._reloadChart();
            });
        });
    }
});

export default {
    resultWidget: publicWidget.registry.SurveyResultWidget,
    chartWidget: publicWidget.registry.SurveyResultChart,
    paginationWidget: publicWidget.registry.SurveyResultPagination
};
