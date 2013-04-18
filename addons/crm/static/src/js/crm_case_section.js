openerp.crm = function(openerp) {
    openerp.web_kanban.KanbanRecord.include({
        renderElement: function () {
            var rendering = this._super();

            if (this.view.dataset.model === 'crm.case.section') {
                var self = this;
                $.when(rendering).done(function() {
                    self.$(".oe_justgage").each(function () {
                        var $el = $(this);
                        var title = $el.html();
                        var unique_id = _.uniqueId("JustGage");
                        $el.empty().css("position", "relative").attr('id', unique_id);

                        new JustGage({
                            id: unique_id,
                            node: this,
                            title: title,
                            value: +$el.data('value'),
                            min: 0,
                            max: +$el.data('max'),
                            relativeGaugeSize: true,
                            humanFriendly: true,
                            titleFontColor: '#333333',
                            valueFontColor: '#333333',
                            labelFontColor: '#000',
                            label: $el.data('label'),
                            levelColors: [
                                "#ff0000",
                                "#f9c802",
                                "#a9d70b"
                            ],
                        });

                        if ($el.data('action')) {
                            $el.click(function (event) {
                                event.stopPropagation();
                                if (!self.view.is_action_enabled('edit')) {
                                    return;
                                }
                                if ($el.find(".oe_justgage_edit").size()) {
                                    $el.find(".oe_justgage_edit").remove();
                                } else {
                                    var $svg = $el.find('svg');
                                    $div = $('<div class="oe_justgage_edit" style="z-index: 1; position: absolute; width: ' + $svg.width() + 'px; top: ' + ($svg.height()/2-5) + 'px;"/>');
                                    $input = $('<input style="text-align: center; width: ' + ($svg.width()-40) + 'px; margin: auto;"/>').val($el.data('value'));
                                    $div.append($input);
                                    $el.prepend($div)
                                    $input.focus()
                                        .keydown(function (event) {
                                            event.stopPropagation();
                                            if (event.keyCode == 13 || event.keyCode == 9) {
                                                if ($input.val() != $el.data('value')) {
                                                    self.view.dataset.call($el.data('action'), [self.id, $input.val()]).then(function () {
                                                        self.do_reload();
                                                    });
                                                } else {
                                                    $div.remove();
                                                }
                                            }
                                        })
                                        .click(function (event) {event.stopPropagation();});
                                }
                            });
                        }
                    });
                    setTimeout(function () {
                        self.$(".oe_sparkline_bar").each(function () {
                            var $el = $(this);
                            $el.data("title", $el.html());
                            $el.sparkline($el.data("value").split(','), {type: 'bar', barWidth: 5} );
                            $el.tipsy({'delayIn': 0, 'html': true, 'title': function(){return $(this).data("title")}, 'gravity': 'n'});
                        });
                    }, 0);
                });
            }
        },
        on_card_clicked: function() {
            if (this.view.dataset.model === 'crm.case.section') {
                this.$('.oe_kanban_crm_salesteams_list a').first().click();
            } else {
                this._super.apply(this, arguments);
            }
        },
    });

};
