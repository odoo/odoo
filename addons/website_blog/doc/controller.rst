.. _controller:

WebsiteBlog(controller)
=======================
Methods
+++++++
 - ``blog`` : remove routing related to date.
 - ``blog_post`` : updated with , suggestion of next post to the user based on
   cookie and number of views.
 - ``discussion`` : added method , contains a detail of discussion on every paragraph,
    if count is true it only return len of ids else return full detail.
        def discussion(self, post_id=0, discussion=None, count=False, **post)
 - ``post_discussion`` : added methodt, that allow to post discussion on any paragraph.
        def post_discussion(self, blog_post_id=0, **post)
 - ``change_bg`` : added method allow a user to change background image on blog 
   post from front-end.
        def change_bg(self, post_id=0, image=None, **post)
 - ``get_user`` : added method , that will return True if user is public else False.
        def get_user(self, **post):
            return [False if request.session.uid else True]

