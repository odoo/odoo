(function () {
    'use strict';

    openerp.website_url = {}

    openerp.website_url.CampaignDialog = openerp.Widget.extend({
        start: function(element) {
            var self = this;

            element.select2({
                minimumInputLength: 1,
                placeholder: ("Campaign name"),
                query: function(q) {
                    $.when(self.fetch_model('crm.tracking.campaign', 'search_campaign', q.term))
                    .then(function(results) {
                        var rs = _.map(results, function(r) {
                            return {id: r.id, text: r.name};
                        });

                        q.callback({
                            more: false,
                            results: rs
                        });
                    });
                },
            });
        },
        fetch_model: function(model, method, term) {
            return openerp.jsonRpc('/web/dataset/call_kw', 'call', {
                model: model,
                method: method,
                args: [term],
                kwargs: {context: openerp.website.get_context()},
            });
        }
    });
})();

$(document).ready(function() {
  var campaign_dialog = new openerp.website_url.CampaignDialog();
  campaign_dialog.start($('#campaign-dialog'));
});

// $(document).ready( function() {


//     ZeroClipboard.config(
//         {swfPath: location.origin + "/website_url/static/src/js/ZeroClipboard.swf" }
//     );
//     var client = new ZeroClipboard($("#btn_shorten_url"));
//     $("#btn_shorten_url").click( function() {
//         if($(this).attr('class').indexOf('btn_copy') === -1) {
//             var url = $("#url").val();
//             openerp.jsonRpc("/r/new", 'call', {'url' : url})
//                 .then(function (result) {
//                     $("#url").data("last_result", result).val(result).focus().select();
//                     $("#btn_shorten_url").text("Copy").removeClass("btn_shorten btn-primary").addClass("btn_copy btn-success");
//                 });
//         }
//     });
//     $("#url").on("change keyup paste mouseup", function() {
//         if ($(this).data("last_result") != $("#url").val()) {
//             $("#btn_shorten_url").text("Shorten").removeClass("btn_copy btn-success").addClass("btn_shorten btn-primary");
//         }
//     });
//     //Testing Data
//     var pie_data = [
//             {
//                 "label" : "India",
//                 "value" : 5
//             },
//             {
//                 "label" : "Africa",
//                 "value" : 10
//             }
//         ];
//     var all_chart_data = [
//     {
//     "key": "Series 1",
//     "values": [ [ 1025409600000 , 0] , [ 1028088000000 , 20] , [ 1030766400000 , 7] , [ 1033358400000 , 1]]
//   },];
//     var hour_chart_data = [
//     {
//     "key": "Series 2",
//     "values": [ [ 1025409600000 , 20] , [ 1028088000000 , 22] , [ 1030766400000 , 23] , [ 1033358400000 , 24]]
//   },];
//   var today_chart_data = [
//     {
//     "key": "Series 1",
//     "values": [ [ 1025409600000 , 0] , [ 1028088000000 , -6.3382185140371] , [ 1030766400000 , -5.9507873460847] , [ 1033358400000 , -11.569146943813]]
//   },];
//   var week_chart_data = [
//     {
//     "key": "Series 1",
//     "values": [ [ 1025409600000 , 0] , [ 1028088000000 , -6.3382185140371] , [ 1030766400000 , -5.9507873460847] , [ 1033358400000 , -11.569146943813]]
//   },];
//   var month_chart_data = [
//     {
//     "key": "Series 1",
//     "values": [ [ 1025409600000 , 0] , [ 1028088000000 , -6.3382185140371] , [ 1030766400000 , -5.9507873460847] , [ 1033358400000 , -11.569146943813]]
//   },];

//     nv.addGraph(function() {
//   var chart = nv.models.pieChart()
//       .x(function(d) { return d.label })
//       .y(function(d) { return d.value })
//       .showLabels(true);


//     d3.select("#pie_chart svg")
//         .datum(pie_data)
//         .transition().duration(1200)
//         .call(chart);

//   return chart;
// });
// nv.addGraph(function() {
//   var chart = nv.models.cumulativeLineChart()
//     .x(function(d) { return d[0] })
//     .y(function(d) { return d[1]})
//     .color(d3.scale.category10().range())
//     .useInteractiveGuideline(true)
//     ;

//   chart.xAxis
//     .tickFormat(function(d) {
//       return d3.time.format('%x')(new Date(d))
//     });

//   d3.select('#all_chart svg')
//     .datum(all_chart_data)
//     .transition().duration(500)
//     .call(chart)
//     ;

//   nv.utils.windowResize(chart.update);

//   return chart;
// });
// nv.addGraph(function() {
//   var chart = nv.models.cumulativeLineChart()
//     .x(function(d) { return d[0] })
//     .y(function(d) { return d[1]})
//     .color(d3.scale.category10().range())
//     .useInteractiveGuideline(true)
//     ;

//   chart.xAxis
//     .tickFormat(function(d) {
//       return d3.time.format('%x')(new Date(d))
//     });

//   d3.select('#hour_chart svg')
//     .datum(hour_chart_data)
//     .transition().duration(500)
//     .call(chart)
//     ;

//   nv.utils.windowResize(chart.update);

//   return chart;
// });
// });
