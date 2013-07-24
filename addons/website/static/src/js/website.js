openerp.website = function(instance) {
var block = ['section', 'div'];
var block_inline = ['p', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'];
var terminal = block.concat(block_inline).join(', ');

instance.website.EditorBar = instance.web.Widget.extend({
    template: 'Website.EditorBar',
    events: {
        'click button[data-action=edit]': 'edit',
        'click button[data-action=save]': 'save',
        'click button[data-action=cancel]': 'cancel',
        'click button[data-action=snippet]': 'snippet',
    },
    container: 'body',
    start: function() {
        var self = this;
        this.saving_mutex = new $.Mutex();
        self.$('button[data-action]').prop('disabled', true);
        self.$('button[data-action=edit], button[data-action=snippet]').prop('disabled', false);
        self.snippet_start();

        $('body').on("keypress", ".oe_editable", function(e) {
            var $e = $(e.currentTarget);
            if (!$e.is('.oe_dirty')) {
                $e.addClass('oe_dirty');
                self.$('button[data-action=save],button[data-action=cancel]').prop('disabled', false);
                // TODO: Are we going to use a meta-data flag in order to know if the field shall be text or html ?
            }
            if (e.which == 13) {
                $e.blur();
                e.preventDefault();
            }
        });

        return this._super.apply(this, arguments);
    },
    edit: function () {
        this.$('button[data-action=edit]').prop('disabled', true);
        var $root = $('[data-oe-model]');
        $root.add($root.find(terminal))
            .not('link, script, span')
            .not(':has(' + terminal + ')')
            .prop('contentEditable', true)
            .addClass('oe_editable')
            .each(function () {
                CKEDITOR.inline(this, {
                    // Don't load ckeditor's style rules
                    stylesSet: [],
                    toolbar: 'Basic',
                    customConfig: '',
                });
            });
    },
    save: function () {
        var self = this;
        var defs = [];
        $('.oe_dirty').each(function (i, v) {
            var $el = $(this);
            // TODO: Add a queue with concurrency limit in webclient
            // https://github.com/medikoo/deferred/blob/master/lib/ext/function/gate.js
            var def = self.saving_mutex.exec(function () {
                return self.saveElement($el).then(function () {
                    $el.removeClass('oe_dirty');
                }).fail(function () {
                    var data = $el.data();
                    console.error(_.str.sprintf('Could not save %s#%d#%s', data.oeModel, data.oeId, data.oeField));
                });
            });
            defs.push(def);
        });
        return $.when.apply(null, defs).then(function () {
            window.location.reload();
        });
    },
    saveElement: function ($el) {
        var data = $el.data();
        var html = $el.html();
        var xpath = data.oeXpath;
        if (xpath) {
            var $w = $el.clone();
            $w.removeClass('oe_dirty');
            _.each(['model', 'id', 'field', 'xpath'], function(d) {$w.removeAttr('data-oe-' + d);});
            $w
                .each(function () { console.log(this); })
                .removeClass('oe_editable')
                .prop('contentEditable', false);
            html = $w.wrap('<div>').parent().html();
        }
        return (new instance.web.DataSet(this, 'ir.ui.view')).call('save', [data.oeModel, data.oeId, data.oeField, html, xpath]);
    },
    cancel: function () {
        window.location.reload();
    },
    snippet_start: function () {
        var self = this;
        $('.oe_snippet').click(function(ev) {
            $('.oe_selected').removeClass('oe_selected');
            var $snippet = $(ev.currentTarget);
            $snippet.addClass('oe_selected');
            $snippet.draggable();
            var selector = $snippet.data("selector");
            var $zone = $(".oe_website_body " + selector);
            var droppable = '<div class="oe_snippet_drop" style="border:1px solid red;">.<br/>.<br/>.<br/>.<br/>.<br/></div>';
            $zone.before(droppable);
            $zone.after(droppable);
            $(".oe_snippet_drop").droppable({
                drop: function( event, ui ) {
                    console.log(event, ui, "DROP");
                    var $target = $(event.target);
                    $target.before($snippet.html());
                    $('.oe_selected').remove();
                    $('.oe_snippet_drop').remove();
                }
            });
        });

    },
    snippet: function (ev) {
        $('.oe_snippet_editor').toggle();
    },
});

$(function(){

    function make_static(){
        $('.oe_snippet_demo').removeClass('oe_new');
        $('.oe_page *').off('mouseover mouseleave');
        $('.oe_page .oe_selected').removeClass('oe_selected');
    }

    var selected_snippet = null;
    function snippet_click(event){
        if(selected_snippet){
            selected_snippet.removeClass('oe_selected');
            if(selected_snippet[0] === $(this)[0]){
                selected_snippet = null;
                event.preventDefault();
                make_static();
                return;
            }
        }
        $(this).addClass('oe_selected');
        selected_snippet = $(this);
        make_editable();
        event.preventDefault();
    }
    //$('.oe_snippet').click(snippet_click);

    var hover_element = null;

    function make_editable( constraint_after, constraint_inside ){
        if(selected_snippet && selected_snippet.hasClass('oe_new')){
            $('.oe_snippet_demo').addClass('oe_new');
        }else{
            $('.oe_snippet_demo').removeClass('oe_new');
        }
    
        $('.oe_page *').off('mouseover');
        $('.oe_page *').off('mouseleave');
        $('.oe_page *').mouseover(function(event){
            console.log('hover:',this);
            if(hover_element){
                hover_element.removeClass('oe_selected');
                hover_element.off('click');
            }
            $(this).addClass('oe_selected');
            $(this).click(append_snippet);
            hover_element = $(this);
            event.stopPropagation();
        });
        $('.oe_page *').mouseleave(function(){
            if(hover_element && $(this) === hover_element){
                hover_element = null;
                $(this).removeClass('oe_selected');
            }
        });
    }

        

    function append_snippet(event){
        console.log('click',this,event.button);
        if(event.button === 0){
            if(selected_snippet){
                if(selected_snippet.hasClass('oe_new')){
                    var new_snippet = $("<div class='oe_snippet'></div>");
                    new_snippet.append($(this).clone());
                    new_snippet.click(snippet_click);
                    $('.oe_snippet.oe_selected').before(new_snippet);
                }else{
                    $(this).after($('.oe_snippet.oe_selected').contents().clone());
                }
                selected_snippet.removeClass('oe_selected');
                selected_snippet = null;
                make_static();
            }
        }else if(event.button === 1){
            $(this).remove();
        }
        event.preventDefault();
    }

});


/**
 * Client action to go back in global history.
 * If can't go back in history stack, will go back to home.
 */
instance.web.ActionGoBack = function(parent, action) {
    window.location.href = document.referrer;
};
instance.web.client_actions.add("goback", "instance.web.ActionGoBack");

};
