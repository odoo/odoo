(function(){
    "use strict";

    var website = openerp.website;
    var _t = openerp._t;
    website.add_template_file('/website_slides/static/src/xml/website_slides.xml');

    website.EditorBarContent.include({
        new_slide: function() {
            new website.editor.AddSlideDialog().appendTo(document.body);
        },
               
    });
    website.editor.AddSlideDialog = website.editor.Dialog.extend({
        template: 'website.addslide.dialog',
        start: function (){
            var r = this._super.apply(this, arguments);
            this.set_tags("");
            return r;
        },

        set_tags: function(tags){
           debugger;
           this.$("input.load_tags").textext({
                plugins: 'tags focus autocomplete ajax',
                tagsItems: tags.split(","),
                // Note: The following list of keyboard keys is added. All entries are default except {32 : 'whitespace!'}.
                keys: {8: 'backspace', 9: 'tab', 13: 'enter!', 27: 'escape!', 37: 'left', 38: 'up!', 39: 'right',
                    40: 'down!', 46: 'delete', 108: 'numpadEnter', 32: 'whitespace!'},
                ajax: {
                    url: '/slides/get_tags',
                    dataType: 'json',
                    cacheResults: true
                }
            });
        }

        });


 
})();
