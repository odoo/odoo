# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.website.sitemap import sitemap_group


@sitemap_group('blog', route_prefixes=('/blog',))
def sitemap_blogs(env, query_string=None):
    blogs = env['blog.blog'].search(env.website.website_domain(), order='sequence')
    slug = env['ir.http']._slug

    def match(loc):
        return not query_string or query_string.lower() in loc.lower()

    if len(blogs) > 1 and match('/blog'):
        yield {'loc': '/blog'}

    for blog in blogs:
        loc = f'/blog/{slug(blog)}'
        if match(loc):
            yield {'loc': loc}


@sitemap_group('blog')
def sitemap_blog_posts(env, query_string=None):
    slug = env['ir.http']._slug
    # TODO: filter posts with env.website.website_domain(); kept unfiltered
    # for strict parity with the legacy sitemap_blog_post behavior.
    posts = env['blog.post'].search([('website_published', '=', True)])

    for post in posts:
        # Canonical path: /blog/<blog>/<post>
        loc = f'/blog/{slug(post.blog_id)}/{slug(post)}'
        if not query_string or query_string.lower() in loc.lower():
            # blog posts should also have lastmod for seo purposes.
            yield {
                'loc': loc,
                'lastmod': (post.write_date or post.create_date).date(),
            }
