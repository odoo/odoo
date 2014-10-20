(function () {
    'use strict';

    openerp.qweb.add_template('/web_graph/static/src/xml/web_graph.xml');

    $(document).ready(function() {
        openerp.footnote = {};
        var _t = openerp._t;



        openerp.reportWidgets = openerp.Widget.extend({
            events: {
                'click .annotable': 'addFootNote',
                'click .foldable': 'fold',
                'click .unfoldable': 'unfold',
                'click .getPDF': 'getPDF',
                'click .saveFootNote': 'saveFootNote',
            },
            start: function() {
                this.footNoteSeqNum = 1;
                var chartAccountId = this.$("select[name='chart_account_id']").val();
                var widget_config = {
                    //stacked : (arch.attrs.stacked === 'True'),
                    mode: 'bar',
                    measures: ['balance'],
                    row_groupby: ['user_type'],
                    //col_groupby: [],
                    //graph_view: this,
                    visible_ui: false,
                    title: 'Assets and Liabilities'
                };
                this.graphWidget = new openerp.web_graph.Graph(
                    this,
                    new openerp.web.Model("account.account"),
                    [],
                    widget_config
                    );
                this.graphWidget.insertBefore(this.$("div.page"));
                return this._super();
            },
            addFootNote: function(e) {
                e.preventDefault();
                if ($(e.target).find("sup").length == 0) {
                    $(e.target).append(' <sup>' + this.footNoteSeqNum + '</sup>');
                    this.$("table").after('<div class="row mt32 mb32"><label for="footnote' + 
                        this.footNoteSeqNum + '">' + this.footNoteSeqNum + '</label><textarea name="footnote' + this.footNoteSeqNum + 
                        '" rows=4 class="form-control">Insert foot note here</textarea><button class="btn btn-primary saveFootNote">Save</button></div>');
                    this.footNoteSeqNum++;
                }
            },
            fold: function(e) {
                e.preventDefault();
                var level = $(e.target).next().html().length
                var el;
                var $el;
                var $nextEls = $(e.target).parent().parent().nextAll();
                for (el in $nextEls) {
                    $el = $($nextEls[el]).find("td span.level");
                    if ($el.html() == undefined)
                        break;
                    if ($el.html().length > level){
                        $el.parent().parent().hide();
                    }
                    else {
                        break;
                    }
                }
                $(e.target).replaceWith('<span class="unfoldable">^</span>');
            },
            unfold: function(e) {
                e.preventDefault();
                var level = $(e.target).next().html().length
                var el;
                var $el;
                var $nextEls = $(e.target).parent().parent().nextAll();
                for (el in $nextEls) {
                    $el = $($nextEls[el]).find("td span.level");
                    if ($el.html() == undefined)
                        break;
                    if ($el.html().length > level){
                        $el.parent().parent().show();
                    }
                    else {
                        break;
                    }
                }
                $(e.target).replaceWith('<span class="foldable">&gt;</span>');                
            },
            getPDF: function(ev) {
                var html = this.$("div.page").parent().html();
                var $field = $('#js_html');
                $field.attr('value', html);
                return ev;
            },
            saveFootNote: function(e) {
                e.preventDefault();
                var num = $(e.target).parent().find("label").text();
                var note = $(e.target).parent().find("textarea").val();
                $(e.target).parent().replaceWith('<div class="row mt32 mb32">' + num + '. ' + note + '</div>')
            }
        });
        var reportWidgets = new openerp.reportWidgets();
        reportWidgets.setElement($('.oe_account_reportWidgets'));
        reportWidgets.start();
    });

})();
