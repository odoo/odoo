# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re

_GROUP_NAME_RE = re.compile(r'^[a-z][a-z0-9_]*$')


class SitemapRegistry:
    """Process-global registry of sitemap URL generators, grouped by name.

    Modules declare their sitemap URLs in a dedicated ``sitemap.py`` file
    instead of tying them to ``@http.route()``::

        from odoo.addons.website.sitemap import sitemap_group

        @sitemap_group('blog', route_prefixes=('/blog',))
        def sitemap_blogs(env, query_string=None):
            yield {'loc': '/blog'}

    Each group is rendered as its own sub-sitemap file referenced by the
    ``/sitemap.xml`` index (e.g. ``sitemap-1-abcd1234-blog-1.xml``).

    Generators have signature ``func(env, query_string=None)`` and yield
    dicts ``{'loc': str}`` with optional ``lastmod``, ``priority`` and
    ``changefreq`` keys. ``env`` is bound to the current website (through
    the context), the website user and the website default language.
    Generators are responsible for their own multi-website filtering,
    typically with ``env.website.website_domain()``.

    ``route_prefixes`` lists URL path prefixes whose controller routes are
    covered by the group: ``Website._enumerate_pages`` skips the
    auto-enumeration of matching routes that carry no explicit ``sitemap``
    kwarg, so converted controllers can drop the kwarg entirely without
    producing duplicate URLs. Routes keeping an explicit
    ``sitemap=True/False/callable`` are never skipped.

    URLs are deduplicated within a group only: the same URL may appear in
    several sub-sitemap files (e.g. a ``website.page`` shadowing a group
    URL), which is harmless per the sitemap protocol. Group generators own
    their URL set entirely; homepage/indexability filtering applied to
    ``website.page`` records does not apply to them.
    """

    def __init__(self):
        self._groups = {}  # name -> [{'func', 'route_prefixes', 'addon'}]

    def register(self, group, func, route_prefixes=()):
        if not _GROUP_NAME_RE.match(group):
            raise ValueError("Invalid sitemap group name %r" % group)
        entries = self._groups.setdefault(group, [])
        if any(entry['func'] is func for entry in entries):
            return
        addon = None
        module = func.__module__ or ''
        if module.startswith('odoo.addons.'):
            addon = module.split('.')[2]
        entries.append({
            'func': func,
            'route_prefixes': tuple(route_prefixes),
            'addon': addon,
        })

    def get_groups(self, loaded_modules=None):
        """Return ``{group_name: [entry, ...]}`` restricted to entries whose
        declaring addon is loaded in the current database registry, so that
        a multi-database process never serves URLs of uninstalled modules.
        """
        groups = {}
        for name, entries in self._groups.items():
            kept = [
                entry for entry in entries
                if loaded_modules is None or entry['addon'] in loaded_modules
            ]
            if kept:
                groups[name] = kept
        return groups

    def get_route_prefixes(self, loaded_modules=None):
        return tuple(
            prefix
            for entries in self.get_groups(loaded_modules).values()
            for entry in entries
            for prefix in entry['route_prefixes']
        )


registry = SitemapRegistry()


def sitemap_group(name, route_prefixes=()):
    """Decorator registering a sitemap URL generator under a named group."""
    def decorator(func):
        registry.register(name, func, route_prefixes)
        return func
    return decorator
