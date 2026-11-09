from odoo import api, models
from odoo.fields import Domain


class Base(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def hierarchy_read(
        self,
        domain,
        specification,
        parent_field_name,
        roots_only=False,
        offset=0,
        limit=None,
        order=None,
        count_limit=None,
    ):
        """ Load the data displayed by the hierarchy view.

        Like :meth:`web_search_read`, return a page of records with the total
        length, plus the parent node to display above them.

        When ``roots_only`` is set, only the roots (records without parent)
        matching ``domain`` are considered. If there is a single root and it
        has children matching ``domain``, it is unfolded: the records are its
        children matching ``domain``, and the root is the parent node.
        Otherwise, the records are the roots. Whether there is a single root
        does not depend on the page.

        When ``roots_only`` is not set, the records are the ones matching
        ``domain``.

        If the root is not unfolded and all the records of the page have the
        same parent, that parent is returned as the parent node, provided the
        current user can read it. This typically happens when ``domain``
        restricts the records to the children of a given parent.

        The page (``offset``, ``limit``, ``order``, ``count_limit``) applies
        to the records only. The parent node is neither part of the page nor
        counted in the length.

        :param domain: the search domain
        :param dict specification: the ``web_read`` specification of the
            records and of the parent node
        :param str parent_field_name: name of the many2one field to the parent
        :param bool roots_only: whether to only consider the roots, typically
            when the search of the view is the default one or empty
        :param int offset: number of records to skip
        :param int limit: maximum number of records to return
        :param str order: sort order of the records
        :param int count_limit: maximum number of records to count
        :return: a dict with the keys:

            - ``parent``: the values of the parent node, or ``False``
            - ``records``: the values of the records of the page
            - ``length``: the number of records matching the domain actually
              searched (the roots, the children of the unfolded root, or
              ``domain``)
        :rtype: dict
        """
        domain = Domain(domain)
        parent = self.browse()

        if roots_only:
            roots_domain = domain & Domain(parent_field_name, '=', False)
            roots = self.search(roots_domain, limit=2, order='id')
            root_children_domain = domain & Domain(parent_field_name, '=', roots.id) if len(roots) == 1 else None
            if root_children_domain is not None and self.search_count(root_children_domain, limit=1):
                parent, domain = roots, root_children_domain
            else:
                domain = roots_domain

        records = self.search_fetch(domain, list(specification), offset=offset, limit=limit, order=order)

        if not parent and len({record[parent_field_name].id for record in records}) == 1:
            parent = records[0][parent_field_name]._filtered_access('read')

        values = (parent + records).web_read(specification)
        return {
            'parent': values[0] if parent else False,
            **self._format_web_search_read_results(domain, values[1:] if parent else values, offset, limit, count_limit),
        }
