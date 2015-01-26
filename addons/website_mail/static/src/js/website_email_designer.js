(function () {
    'use strict';
    openerp.website.EditorBar.include({
        start: function () {
            if (location.search.indexOf("enable_editor") !== -1) {
                this.on('rte:ready', this, function () {
                    $("#choose_template").show();

                    var $editable = $("#wrapwrap .o_editable:first");

                    $("#choose_template").off("click").on("click", function (event) {
                        $editable.parent().add("#oe_snippets, #templates").toggleClass("hidden");
                        $(this).first().toggleClass("hidden");
                        $(this).last().toggleClass("hidden");
                        var $iframe = $("iframe", window.top.document).filter(function () {
                            return $(this).contents()[0] === document;
                        });
                        $iframe.css("height", Math.max(300,$("body")[0].scrollHeight+20)+"px");
                        event.preventDefault();
                    });
                    $(".js_template_set").off("click").on("click", function (event) {
                        openerp.website.editor_bar.rte.historyRecordUndo($editable);
                        $editable.html( $(this).parent().find(".js_content").html() );
                        $editable.parent().add("#oe_snippets, #templates").toggleClass("hidden");
                        event.preventDefault();
                    });
                });
            }
            return this._super.apply(this, arguments);
        }
    });
})();
