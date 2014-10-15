$(document).ready(function() {
    "use strict";

    var website = openerp.website;
    var _t = openerp._t;

    website.EditorBarContent.include({
        new_blog_post: function() {
            website.prompt({
                id: "editor_new_blog",
                window_title: _t("New Blog Post"),
                select: "Select Blog",
                init: function (field) {
                    return website.session.model('blog.blog')
                            .call('name_search', [], { context: website.get_context() });
                },
            }).then(function (cat_id) {
                document.location = '/blogpost/new?blog_id=' + cat_id;
            });
        },
    });
    if ($('.website_blog').length) {
        website.EditorBar.include({
            edit: function () {
                var self = this;
                $('.popover').remove();
                this._super();
                var vHeight = $(window).height();
                $('body').on('click','#change_cover',_.bind(this.change_bg, self.rte.editor, vHeight));
                $('body').on('click', '#clear_cover',_.bind(this.clean_bg, self.rte.editor, vHeight));
            },
            save : function() {
                var res = this._super();
                if ($('.cover').length) {
                    openerp.jsonRpc("/blogpost/change_background", 'call', {
                        'post_id' : $('#blog_post_name').attr('data-oe-id'),
                        'image' : $('.cover').css('background-image').replace(/url\(|\)|"|'/g,''),
                    });
                }
                return res;
            },
            clean_bg : function(vHeight) {
                $('.js_fullheight').css({"background-image":'none', 'min-height': vHeight});
            },
            change_bg : function(vHeight) {
                var self  = this;
                var element = new CKEDITOR.dom.element(self.element.find('.cover-storage').$[0]);
                var editor  = new website.editor.MediaDialog(self, element);
                $(document.body).on('media-saved', self, function (o) {
                    var url = $('.cover-storage').attr('src');
                    $('.js_fullheight').css({"background-image": !_.isUndefined(url) ? 'url(' + url + ')' : "", 'min-height': vHeight});
                    $('.cover-storage').hide();
                });
                editor.appendTo('body');
            },
        });
    }

    website.snippet.options.website_blogpost = website.snippet.Option.extend({
        start: function () {
            var self = this;
            this.blogpost_id = parseInt(this.$target.find('[data-oe-model="blog.post"]').data('oe-id'));
            var size_x = parseInt(this.$target.attr("colspan") || 1);
            var size_y = parseInt(this.$target.attr("rowspan") || 1);

            var $size = this.$el.find('ul[name="size"]');
            var $select = $size.find('tr:eq(0) td:lt('+size_x+')');
            if (size_y >= 2) $select = $select.add($size.find('tr:eq(1) td:lt('+size_x+')'));
            if (size_y >= 3) $select = $select.add($size.find('tr:eq(2) td:lt('+size_x+')'));
            if (size_y >= 4) $select = $select.add($size.find('tr:eq(3) td:lt('+size_x+')'));
            $select.addClass("selected");
            this.bind_resize();
        },
        reload: function () {
            if (location.href.match(/\?enable_editor/)) {
                location.reload();
            } else {
                location.href = location.href.replace(/\?(enable_editor=1&)?|#.*|$/, '?enable_editor=1&');
            }
        },
        bind_resize: function () {
            var self = this;
            var $table = this.$el.find('ul[name="size"] table');
            var get_index = function(event){
                return [$(event.currentTarget).index()+1, $(event.currentTarget).parent().index()+1];
            } ;
            this.$el.on('mouseover', 'ul[name="size"] td', function (event) {
                var index = get_index(event); 
                $table.find("td").removeClass("select");
                _.each(_.range(0, index[1]), function(y_index){
                    _.each(_.range(0, index[0]), function(x_index){
                        $table.find("tr:eq("+y_index+") td:eq("+x_index+")").addClass("select");
                    });
                });
            });
            this.$el.on('click', 'ul[name="size"] td', function (event) {
                var index = get_index(event);
                openerp.jsonRpc('/blogpost/change_size', 'call', {'blogpost_id': self.blogpost_id, 'x': index[0], 'y': index[1]})
                    .then(self.reload);
            });
        },
        go_to: function (type, value) {
            if(type !== "click") return;
            openerp.jsonRpc('/blogpost/change_sequence', 'call', {'blogpost_id': this.blogpost_id, 'sequence': value})
                .then(this.reload);
        }
    });
});
